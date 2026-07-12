"""Findings endpoints: the canonical, deduplicated view."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vulnconsole.contexts.identity.api.deps import Principal, require_permission
from vulnconsole.contexts.identity.application.permissions import FINDINGS_READ, FINDINGS_WRITE
from vulnconsole.contexts.normalization.application import service
from vulnconsole.contexts.normalization.application.schemas import (
    AssignRequest,
    FindingDetailOut,
    FindingOut,
    FindingSourceOut,
    TransitionRequest,
)
from vulnconsole.contexts.normalization.domain.models import (
    FINDING_STATUSES,
    Finding,
    FindingSource,
)
from vulnconsole.contexts.normalization.domain.sla import OPEN_STATUSES
from vulnconsole.contexts.normalization.domain.triage import allowed_transitions
from vulnconsole.shared.db import get_db_session
from vulnconsole.shared.deps import get_event_bus
from vulnconsole.shared.events import EventBus
from vulnconsole.shared.pagination import (
    DEFAULT_LIMIT,
    Page,
    PageMeta,
    clamp_limit,
    decode_cursor,
    encode_cursor,
)
from vulnconsole.shared.problems import ProblemError

router = APIRouter(tags=["findings"])

SEVERITIES = ("critical", "high", "medium", "low", "info")


def _csv_filter(raw: str | None, allowed: tuple[str, ...], field: str) -> list[str] | None:
    if raw is None:
        return None
    values = [value.strip() for value in raw.split(",") if value.strip()]
    unknown = [value for value in values if value not in allowed]
    if unknown:
        raise ProblemError(
            status=422,
            title="Invalid filter",
            detail=f"Unknown {field} value(s): {', '.join(unknown)}",
            slug="invalid-filter",
        )
    return values or None


@router.get("/findings", response_model=Page[FindingOut])
async def list_findings(
    principal: Annotated[Principal, Depends(require_permission(FINDINGS_READ))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    severity: str | None = None,
    status: str | None = None,
    repository: str | None = None,
    finding_class: str | None = None,
    tool: str | None = None,
    cve: str | None = None,
    owner: str | None = None,
    overdue: bool = False,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> Page[FindingOut]:
    limit = clamp_limit(limit)
    query = select(Finding).order_by(Finding.first_seen.desc(), Finding.id.desc())

    severities = _csv_filter(severity, SEVERITIES, "severity")
    if severities:
        query = query.where(Finding.severity.in_(severities))
    statuses = _csv_filter(status, FINDING_STATUSES, "status")
    if statuses:
        query = query.where(Finding.status.in_(statuses))
    if repository:
        query = query.where(Finding.repository == repository)
    if finding_class:
        query = query.where(Finding.finding_class == finding_class)
    if tool:
        query = query.where(Finding.tool_names.contains([tool.lower()]))
    if cve:
        query = query.where(Finding.cve_id == cve.strip().upper())
    if owner:
        query = query.where(Finding.owner == owner)
    if overdue:
        query = query.where(
            Finding.sla_due_at.is_not(None),
            Finding.sla_due_at < datetime.now(UTC),
            Finding.status.in_(tuple(OPEN_STATUSES)),
        )
    if cursor:
        position = decode_cursor(cursor)
        first_seen = datetime.fromisoformat(str(position["f"]))
        last_id = uuid.UUID(str(position["i"]))
        query = query.where(
            (Finding.first_seen < first_seen)
            | ((Finding.first_seen == first_seen) & (Finding.id < last_id))
        )

    rows = list(await session.scalars(query.limit(limit + 1)))
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        encode_cursor({"f": rows[-1].first_seen.isoformat(), "i": str(rows[-1].id)})
        if has_more and rows
        else None
    )
    return Page(
        data=[FindingOut.from_finding(row) for row in rows],
        pagination=PageMeta(next_cursor=next_cursor, has_more=has_more, limit=limit),
    )


@router.get("/findings/{finding_id}", response_model=FindingDetailOut)
async def get_finding(
    finding_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_permission(FINDINGS_READ))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FindingDetailOut:
    finding = await session.get(Finding, finding_id)
    if finding is None:
        raise ProblemError(
            status=404, title="Not found", detail="Finding not found", slug="not-found"
        )
    sources = await session.scalars(
        select(FindingSource)
        .where(FindingSource.finding_id == finding_id)
        .order_by(FindingSource.created_at)
    )
    detail = FindingDetailOut(
        **FindingOut.from_finding(finding).model_dump(),
        sources=[FindingSourceOut.model_validate(source) for source in sources],
        allowed_transitions=list(allowed_transitions(finding.status)),
    )
    return detail


@router.post("/findings/{finding_id}/transition", response_model=FindingOut)
async def transition_finding(
    finding_id: uuid.UUID,
    body: TransitionRequest,
    principal: Annotated[Principal, Depends(require_permission(FINDINGS_WRITE))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    bus: Annotated[EventBus, Depends(get_event_bus)],
) -> FindingOut:
    finding = await service.change_status(
        session,
        bus,
        finding_id=finding_id,
        target=body.status,
        reason=body.reason,
        actor=principal.actor,
        risk_accepted_until=body.risk_accepted_until,
    )
    return FindingOut.from_finding(finding)


@router.put("/findings/{finding_id}/assignment", response_model=FindingOut)
async def assign_finding(
    finding_id: uuid.UUID,
    body: AssignRequest,
    principal: Annotated[Principal, Depends(require_permission(FINDINGS_WRITE))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    bus: Annotated[EventBus, Depends(get_event_bus)],
) -> FindingOut:
    owner = body.owner.strip() if body.owner else None
    finding = await service.assign_finding(
        session, bus, finding_id=finding_id, owner=owner or None, actor=principal.actor
    )
    return FindingOut.from_finding(finding)
