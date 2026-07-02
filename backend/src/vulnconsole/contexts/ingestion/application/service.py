"""Ingestion application services: scan creation (API) and parsing (worker)."""

import re
import uuid

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from vulnconsole.contexts.identity.application.service import record_audit
from vulnconsole.contexts.ingestion.connectors.base import (
    Connector,
    ConnectorError,
    get_connector,
    sniff_format,
    supported_formats,
)
from vulnconsole.contexts.ingestion.domain.models import (
    SCAN_STATUS_FAILED,
    SCAN_STATUS_NORMALIZED,
    SCAN_STATUS_PARSED,
    SCAN_STATUS_RECEIVED,
    RawFinding,
    Scan,
)
from vulnconsole.contexts.ingestion.infrastructure import artifacts
from vulnconsole.shared.config import get_settings
from vulnconsole.shared.events import (
    SCAN_FAILED,
    SCAN_PARSED,
    SCAN_RECEIVED,
    EventBus,
    EventEnvelope,
)
from vulnconsole.shared.ids import uuid7
from vulnconsole.shared.problems import ProblemError

logger = structlog.get_logger(__name__)

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]")


def _sanitize_filename(filename: str | None) -> str:
    if not filename:
        return "artifact"
    basename = filename.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = _SAFE_FILENAME.sub("_", basename)[:120]
    return cleaned or "artifact"


def _resolve_connector(content: bytes, format_id: str | None) -> Connector:
    if format_id:
        connector = get_connector(format_id)
        if connector is None:
            raise ProblemError(
                status=422,
                title="Unsupported format",
                detail=f"Unknown format {format_id!r}; supported: {', '.join(supported_formats())}",
                slug="unsupported-format",
            )
        return connector
    connector = sniff_format(content)
    if connector is None:
        raise ProblemError(
            status=422,
            title="Unsupported format",
            detail=f"Could not detect the format; supported: {', '.join(supported_formats())}",
            slug="unsupported-format",
        )
    return connector


async def create_scan(
    session: AsyncSession,
    bus: EventBus,
    *,
    actor: str,
    repository: str,
    branch: str | None,
    commit_sha: str | None,
    filename: str | None,
    content: bytes,
    format_id: str | None = None,
) -> Scan:
    settings = get_settings()
    if len(content) == 0:
        raise ProblemError(
            status=422, title="Empty upload", detail="The artifact is empty", slug="empty-upload"
        )
    if len(content) > settings.max_upload_bytes:
        raise ProblemError(
            status=413,
            title="Artifact too large",
            detail=f"Limit is {settings.max_upload_bytes} bytes",
            slug="too-large",
        )

    connector = _resolve_connector(content, format_id)
    scan_id = uuid7()
    artifact_key = f"scans/{scan_id}/{_sanitize_filename(filename)}"
    await artifacts.store_artifact(artifact_key, content)

    scan = Scan(
        id=scan_id,
        repository=repository,
        branch=branch,
        commit_sha=commit_sha,
        format=connector.format_id,
        status=SCAN_STATUS_RECEIVED,
        artifact_key=artifact_key,
        artifact_size=len(content),
        created_by=actor,
    )
    session.add(scan)
    record_audit(
        session,
        actor=actor,
        action="scan.created",
        entity_type="scan",
        entity_id=str(scan.id),
        detail={"repository": repository, "format": connector.format_id, "size": len(content)},
    )
    await session.commit()

    try:
        await bus.publish(
            EventEnvelope(
                subject=SCAN_RECEIVED,
                actor=actor,
                correlation_id=str(scan.id),
                payload={"scan_id": str(scan.id), "format": scan.format},
            )
        )
    except Exception as exc:
        logger.error("scan.publish_failed", scan_id=str(scan.id), error=str(exc))
        scan.status = SCAN_STATUS_FAILED
        scan.error = "event bus unavailable; re-upload once the platform is healthy"
        await session.commit()
        raise ProblemError(
            status=503,
            title="Event bus unavailable",
            detail="The scan was stored but could not be queued; re-upload later",
            slug="bus-unavailable",
        ) from exc
    return scan


async def get_scan(session: AsyncSession, scan_id: uuid.UUID) -> Scan | None:
    return await session.get(Scan, scan_id)


async def parse_scan(session: AsyncSession, bus: EventBus, scan_id: uuid.UUID) -> None:
    """Worker side: fetch the artifact, parse it, persist raw findings."""
    scan = await get_scan(session, scan_id)
    if scan is None:
        logger.warning("scan.parse_skipped", scan_id=str(scan_id), reason="not found")
        return
    if scan.status != SCAN_STATUS_RECEIVED:
        logger.info("scan.parse_skipped", scan_id=str(scan_id), status=scan.status)
        return

    connector = get_connector(scan.format)
    if connector is None:  # format was validated at upload; connector set changed since
        await _fail_scan(session, bus, scan, f"no connector for format {scan.format!r}")
        return

    try:
        content = await artifacts.fetch_artifact(scan.artifact_key)
        result = connector.parse(content)
    except ConnectorError as exc:
        await _fail_scan(session, bus, scan, str(exc))
        return

    # Idempotent re-parse: drop any rows from a previous partial attempt.
    await session.execute(delete(RawFinding).where(RawFinding.scan_id == scan.id))
    for draft in result.findings:
        session.add(
            RawFinding(
                scan_id=scan.id,
                finding_class=draft.finding_class,
                rule_id=draft.rule_id,
                severity=draft.severity,
                title=draft.title,
                file_path=draft.file_path,
                line=draft.line,
                payload=draft.payload,
                hints=draft.hints,
            )
        )
    scan.tool_name = result.tool_name
    scan.status = SCAN_STATUS_PARSED
    await session.commit()
    logger.info("scan.parsed", scan_id=str(scan.id), raw_findings=len(result.findings))

    await bus.publish(
        EventEnvelope(
            subject=SCAN_PARSED,
            correlation_id=str(scan.id),
            payload={"scan_id": str(scan.id), "raw_finding_count": len(result.findings)},
        )
    )


async def _fail_scan(session: AsyncSession, bus: EventBus, scan: Scan, error: str) -> None:
    scan.status = SCAN_STATUS_FAILED
    scan.error = error[:2000]
    await session.commit()
    logger.error("scan.failed", scan_id=str(scan.id), error=error)
    await bus.publish(
        EventEnvelope(
            subject=SCAN_FAILED,
            correlation_id=str(scan.id),
            payload={"scan_id": str(scan.id), "error": error[:500]},
        )
    )


async def list_raw_findings(session: AsyncSession, scan_id: uuid.UUID) -> list[RawFinding]:
    result = await session.scalars(
        select(RawFinding).where(RawFinding.scan_id == scan_id).order_by(RawFinding.id)
    )
    return list(result)


async def mark_scan_normalized(session: AsyncSession, scan_id: uuid.UUID) -> None:
    """Called by the normalization context once canonical findings are persisted."""
    scan = await get_scan(session, scan_id)
    if scan is not None:
        scan.status = SCAN_STATUS_NORMALIZED
