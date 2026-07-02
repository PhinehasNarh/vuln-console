"""Findings endpoints: the canonical, deduplicated view."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vulnconsole.contexts.identity.api.deps import Principal, require_permission
from vulnconsole.contexts.identity.domain.roles import FINDINGS_READ
from vulnconsole.contexts.normalization.application.schemas import (
    FindingDetailOut,
    FindingOut,
    FindingSourceOut,
)
from vulnconsole.contexts.normalization.domain.models import FINDING_STATUSES, Finding, FindingSource
from vulnconsole.shared.db import get_db_session
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
        data=[FindingOut.model_validate(row) for row in rows],
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
        **FindingOut.model_validate(finding).model_dump(),
        sources=[FindingSourceOut.model_validate(source) for source in sources],
    )
    return detail
