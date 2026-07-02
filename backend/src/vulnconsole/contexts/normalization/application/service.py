"""Normalization application service: raw findings to canonical findings."""

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vulnconsole.contexts.ingestion.application import service as ingestion_service
from vulnconsole.contexts.ingestion.domain.models import (
    SCAN_STATUS_NORMALIZED,
    SCAN_STATUS_PARSED,
)
from vulnconsole.contexts.normalization.domain.fingerprint import (
    compute_fingerprint,
    derive_identity,
)
from vulnconsole.contexts.normalization.domain.models import Finding, FindingSource
from vulnconsole.shared.events import FINDING_CREATED, FINDING_UPDATED, EventBus, EventEnvelope

logger = structlog.get_logger(__name__)

_SEVERITY_ORDER = ("info", "low", "medium", "high", "critical")


def _severity_rank(severity: str) -> int:
    try:
        return _SEVERITY_ORDER.index(severity)
    except ValueError:
        return 0


async def normalize_scan(session: AsyncSession, bus: EventBus, scan_id: uuid.UUID) -> None:
    scan = await ingestion_service.get_scan(session, scan_id)
    if scan is None:
        logger.warning("normalize.skipped", scan_id=str(scan_id), reason="scan not found")
        return
    if scan.status == SCAN_STATUS_NORMALIZED:
        logger.info("normalize.skipped", scan_id=str(scan_id), reason="already normalized")
        return
    if scan.status != SCAN_STATUS_PARSED:
        logger.warning("normalize.skipped", scan_id=str(scan_id), status=scan.status)
        return

    raws = await ingestion_service.list_raw_findings(session, scan_id)
    raw_ids = [raw.id for raw in raws]
    already_linked: set[uuid.UUID] = set()
    if raw_ids:
        linked = await session.scalars(
            select(FindingSource.raw_finding_id).where(FindingSource.raw_finding_id.in_(raw_ids))
        )
        already_linked = set(linked)

    tool = (scan.tool_name or scan.format).lower()
    now = datetime.now(UTC)
    seen_this_run: dict[str, Finding] = {}
    created_ids: set[uuid.UUID] = set()
    updated_ids: set[uuid.UUID] = set()

    for raw in raws:
        if raw.id in already_linked:
            continue
        hints: dict[str, str] = raw.hints or {}
        rule_key, location_key = derive_identity(
            finding_class=raw.finding_class,
            tool=tool,
            rule_id=raw.rule_id,
            file_path=raw.file_path,
            hints=hints,
        )
        fingerprint = compute_fingerprint(
            finding_class=raw.finding_class,
            rule_key=rule_key,
            asset_key=scan.repository,
            location_key=location_key,
        )
        package = hints.get("package")
        if package and hints.get("installed_version"):
            package = f"{package}@{hints['installed_version']}"
        vuln_id = hints.get("vuln_id")

        finding = seen_this_run.get(fingerprint) or await session.scalar(
            select(Finding).where(Finding.fingerprint == fingerprint)
        )
        if finding is None:
            finding = Finding(
                fingerprint=fingerprint,
                finding_class=raw.finding_class,
                rule_key=rule_key,
                title=raw.title,
                severity=raw.severity,
                repository=scan.repository,
                file_path=raw.file_path,
                line=raw.line,
                package=package,
                cve_id=vuln_id,
                fixed_version=hints.get("fixed_version"),
                tool_names=[tool],
                first_seen=now,
                last_seen=now,
            )
            session.add(finding)
            await session.flush()
            created_ids.add(finding.id)
        else:
            finding.last_seen = now
            # Keep the worst severity across scanners rather than the latest word.
            if _severity_rank(raw.severity) > _severity_rank(finding.severity):
                finding.severity = raw.severity
                finding.title = raw.title
            finding.line = raw.line if raw.line is not None else finding.line
            finding.package = package or finding.package
            finding.cve_id = vuln_id or finding.cve_id
            finding.fixed_version = hints.get("fixed_version") or finding.fixed_version
            if tool not in finding.tool_names:
                finding.tool_names = [*finding.tool_names, tool]
            if finding.id not in created_ids:
                updated_ids.add(finding.id)
        seen_this_run[fingerprint] = finding
        session.add(FindingSource(finding_id=finding.id, raw_finding_id=raw.id, scan_id=scan.id))

    await ingestion_service.mark_scan_normalized(session, scan_id)
    await session.commit()
    logger.info(
        "scan.normalized",
        scan_id=str(scan_id),
        created=len(created_ids),
        updated=len(updated_ids),
    )

    for finding_id in created_ids:
        await bus.publish(
            EventEnvelope(
                subject=FINDING_CREATED,
                correlation_id=str(scan_id),
                payload={"finding_id": str(finding_id)},
            )
        )
    for finding_id in updated_ids:
        await bus.publish(
            EventEnvelope(
                subject=FINDING_UPDATED,
                correlation_id=str(scan_id),
                payload={"finding_id": str(finding_id)},
            )
        )
