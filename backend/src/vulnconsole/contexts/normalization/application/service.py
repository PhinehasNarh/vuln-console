"""Normalization application service: raw findings to canonical findings."""

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vulnconsole.contexts.ingestion.application import service as ingestion_service
from vulnconsole.contexts.ingestion.application.service import (
    SCAN_STATUS_NORMALIZED,
    SCAN_STATUS_PARSED,
)
from vulnconsole.contexts.normalization.application.schemas import FindingOut
from vulnconsole.contexts.normalization.domain.fingerprint import (
    compute_fingerprint,
    derive_identity,
)
from vulnconsole.contexts.normalization.domain.models import Finding, FindingSource
from vulnconsole.contexts.normalization.domain.sla import (
    OPEN_STATUSES,
    compute_due_at,
    is_open,
)
from vulnconsole.contexts.normalization.domain.triage import (
    is_allowed,
    is_valid_status,
    requires_expiry,
)
from vulnconsole.shared.events import (
    FINDING_ASSIGNED,
    FINDING_CREATED,
    FINDING_STATUS_CHANGED,
    FINDING_UPDATED,
    SLA_BREACHED,
    EventBus,
    EventEnvelope,
)
from vulnconsole.shared.problems import ProblemError

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
                sla_due_at=compute_due_at(now, raw.severity),
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
                # A worse severity tightens the SLA; recompute from first_seen.
                finding.sla_due_at = compute_due_at(finding.first_seen, raw.severity)
                finding.sla_breach_notified_at = None
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


async def get_finding(session: AsyncSession, finding_id: uuid.UUID) -> Finding | None:
    return await session.get(Finding, finding_id)


async def list_findings_created_between(
    session: AsyncSession, *, since: datetime, until: datetime, limit: int = 2000
) -> list[FindingOut]:
    """Canonical findings first seen within a window, for time-framed reports."""
    result = await session.scalars(
        select(Finding)
        .where(Finding.first_seen >= since, Finding.first_seen <= until)
        .order_by(Finding.severity, Finding.first_seen.desc())
        .limit(limit)
    )
    return [FindingOut.from_finding(row) for row in result]


async def assign_finding(
    session: AsyncSession,
    bus: EventBus,
    *,
    finding_id: uuid.UUID,
    owner: str | None,
    actor: str,
) -> Finding:
    """Set (or clear, when owner is None) the engineer responsible for a finding."""
    from vulnconsole.contexts.identity.application.service import record_audit

    finding = await session.get(Finding, finding_id)
    if finding is None:
        raise ProblemError(
            status=404, title="Not found", detail="Finding not found", slug="not-found"
        )
    previous = finding.owner
    finding.owner = owner
    finding.assigned_at = datetime.now(UTC) if owner else None
    record_audit(
        session,
        actor=actor,
        action="finding.assigned" if owner else "finding.unassigned",
        entity_type="finding",
        entity_id=str(finding.id),
        detail={"from": previous, "to": owner},
    )
    await session.commit()

    if owner:
        await bus.publish(
            EventEnvelope(
                subject=FINDING_ASSIGNED,
                actor=actor,
                correlation_id=str(finding.id),
                payload={"finding_id": str(finding.id), "owner": owner, "previous": previous},
            )
        )
    return finding


async def change_status(
    session: AsyncSession,
    bus: EventBus,
    *,
    finding_id: uuid.UUID,
    target: str,
    reason: str,
    actor: str,
    risk_accepted_until: datetime | None = None,
    system: bool = False,
) -> Finding:
    """Transition a finding's lifecycle status with a mandatory justification."""
    from vulnconsole.contexts.identity.application.service import record_audit

    finding = await session.get(Finding, finding_id)
    if finding is None:
        raise ProblemError(
            status=404, title="Not found", detail="Finding not found", slug="not-found"
        )
    reason = (reason or "").strip()
    if not reason:
        raise ProblemError(
            status=422,
            title="Justification required",
            detail="A reason is required for every status change",
            slug="reason-required",
        )
    if not is_valid_status(target):
        raise ProblemError(
            status=422,
            title="Invalid status",
            detail=f"Unknown status {target!r}",
            slug="invalid-status",
        )
    if not is_allowed(finding.status, target):
        raise ProblemError(
            status=422,
            title="Illegal transition",
            detail=f"Cannot move a finding from {finding.status!r} to {target!r}",
            slug="illegal-transition",
        )
    now = datetime.now(UTC)
    if requires_expiry(target):
        if risk_accepted_until is None:
            raise ProblemError(
                status=422,
                title="Expiry required",
                detail="Risk acceptance requires an expiry date",
                slug="expiry-required",
            )
        if risk_accepted_until <= now:
            raise ProblemError(
                status=422,
                title="Expiry in the past",
                detail="The risk-acceptance expiry must be in the future",
                slug="expiry-past",
            )

    previous = finding.status
    finding.status = target
    finding.status_reason = reason
    finding.status_changed_at = now
    finding.status_changed_by = actor
    finding.risk_accepted_until = risk_accepted_until if target == "risk_accepted" else None
    # Reopening puts the finding back under SLA pressure; let breaches fire again.
    if target == "reopened":
        finding.sla_breach_notified_at = None

    record_audit(
        session,
        actor=actor,
        action="finding.status_changed",
        entity_type="finding",
        entity_id=str(finding.id),
        detail={"from": previous, "to": target, "reason": reason, "system": system},
    )
    await session.commit()

    await bus.publish(
        EventEnvelope(
            subject=FINDING_STATUS_CHANGED,
            actor=actor,
            correlation_id=str(finding.id),
            payload={
                "finding_id": str(finding.id),
                "from": previous,
                "status": target,
                "reason": reason,
            },
        )
    )
    return finding


async def reopen_expired_acceptances(session: AsyncSession, bus: EventBus) -> int:
    """Auto-reopen risk-accepted findings whose acceptance has expired."""
    now = datetime.now(UTC)
    expired = await session.scalars(
        select(Finding).where(
            Finding.status == "risk_accepted",
            Finding.risk_accepted_until.is_not(None),
            Finding.risk_accepted_until < now,
        )
    )
    ids = [finding.id for finding in expired]
    for finding_id in ids:
        await change_status(
            session,
            bus,
            finding_id=finding_id,
            target="reopened",
            reason="Risk acceptance expired",
            actor="system:expiry",
            system=True,
        )
    if ids:
        logger.info("triage.acceptances_reopened", count=len(ids))
    return len(ids)


async def scan_sla_breaches(session: AsyncSession, bus: EventBus) -> int:
    """Emit risk.sla.breached for open findings past due that have not fired yet.

    Idempotent: sla_breach_notified_at is stamped so each breach fires once.
    Returns the number of new breaches emitted.
    """
    now = datetime.now(UTC)
    overdue = await session.scalars(
        select(Finding).where(
            Finding.sla_due_at.is_not(None),
            Finding.sla_due_at < now,
            Finding.sla_breach_notified_at.is_(None),
            Finding.status.in_(tuple(OPEN_STATUSES)),
        )
    )
    breached = list(overdue)
    for finding in breached:
        finding.sla_breach_notified_at = now
    if breached:
        await session.commit()
    for finding in breached:
        await bus.publish(
            EventEnvelope(
                subject=SLA_BREACHED,
                correlation_id=str(finding.id),
                payload={
                    "finding_id": str(finding.id),
                    "severity": finding.severity,
                    "owner": finding.owner,
                    "due_at": finding.sla_due_at.isoformat() if finding.sla_due_at else None,
                },
            )
        )
    if breached:
        logger.info("sla.breaches_emitted", count=len(breached))
    return len(breached)


def finding_is_open(status: str) -> bool:
    return is_open(status)
