"""Report export endpoints."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from vulnconsole.contexts.identity.api.deps import Principal, require_permission
from vulnconsole.contexts.identity.application.permissions import FINDINGS_READ
from vulnconsole.contexts.reporting.application.report import build_report
from vulnconsole.contexts.reporting.infrastructure.logo import logo_data_uri
from vulnconsole.contexts.reporting.infrastructure.render import render_html
from vulnconsole.shared.config import get_settings
from vulnconsole.shared.db import get_db_session
from vulnconsole.shared.problems import ProblemError

router = APIRouter(tags=["reporting"])

MAX_RANGE_DAYS = 366


@router.get("/reports/audit", response_class=Response)
async def audit_report(
    principal: Annotated[Principal, Depends(require_permission(FINDINGS_READ))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    since: datetime | None = None,
    until: datetime | None = None,
) -> Response:
    settings = get_settings()
    until = until or datetime.now(UTC)
    since = since or (until - timedelta(days=settings.report_default_days))
    if since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    if since >= until:
        raise ProblemError(
            status=422,
            title="Invalid range",
            detail="'since' must be before 'until'",
            slug="invalid-range",
        )
    if (until - since) > timedelta(days=MAX_RANGE_DAYS):
        raise ProblemError(
            status=422,
            title="Range too large",
            detail=f"The reporting period may not exceed {MAX_RANGE_DAYS} days",
            slug="range-too-large",
        )

    data = await build_report(
        session,
        since=since,
        until=until,
        generated_by=principal.name,
        company_name=settings.report_company_name,
        confidential_label=settings.report_confidential_label,
    )
    html = render_html(data, logo_data_uri(settings.report_logo_path))
    filename = f"audit-report-{since.date()}-to-{until.date()}.html"
    return Response(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
