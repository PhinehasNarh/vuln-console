"""Assemble a time-framed audit report: summary, findings, and the incident
timeline built from the audit log.

Reporting reads other contexts only through their application layer (ADR-0002).
"""

from collections import Counter
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from vulnconsole.contexts.identity.application import service as identity_service
from vulnconsole.contexts.identity.application.schemas import AuditEventOut
from vulnconsole.contexts.normalization.application import service as normalization_service
from vulnconsole.contexts.normalization.application.schemas import FindingOut

SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")

# Audit action -> (category, human-readable template). {to}/{from} fill from detail.
_ACTION_TEXT: dict[str, tuple[str, str]] = {
    "scan.created": ("ingest", "Scan uploaded to {repository}"),
    "finding.assigned": ("triage", "Finding assigned to {to}"),
    "finding.unassigned": ("triage", "Finding assignment cleared"),
    "user.created": ("identity", "User account {username} created"),
    "api_token.created": ("identity", "API token {name} created"),
    "auth.login": ("identity", "Signed in"),
    "auth.login_failed": ("security", "Failed sign-in attempt"),
    "authz.denied": ("security", "Access denied ({permission})"),
}


class TimelineEvent(BaseModel):
    at: datetime
    actor: str
    category: str
    summary: str


class ReportSummary(BaseModel):
    total_findings: int
    by_severity: dict[str, int]
    overdue: int
    assigned: int
    unassigned: int
    repositories: int


class ReportData(BaseModel):
    company_name: str
    confidential_label: str
    generated_by: str
    generated_at: datetime
    since: datetime
    until: datetime
    summary: ReportSummary
    findings: list[FindingOut]
    timeline: list[TimelineEvent]


def _describe(event: AuditEventOut) -> TimelineEvent:
    category, template = _ACTION_TEXT.get(event.action, ("event", event.action.replace(".", " ")))
    detail = {k: str(v) for k, v in (event.detail or {}).items() if v is not None}
    try:
        summary = template.format(**detail)
    except (KeyError, IndexError):
        summary = template
    return TimelineEvent(
        at=event.created_at, actor=event.actor, category=category, summary=summary
    )


def _summarize(findings: list[FindingOut]) -> ReportSummary:
    by_severity = Counter(f.severity for f in findings)
    return ReportSummary(
        total_findings=len(findings),
        by_severity={sev: by_severity.get(sev, 0) for sev in SEVERITY_ORDER},
        overdue=sum(1 for f in findings if f.sla_status == "overdue"),
        assigned=sum(1 for f in findings if f.owner),
        unassigned=sum(1 for f in findings if not f.owner),
        repositories=len({f.repository for f in findings}),
    )


async def build_report(
    session: AsyncSession,
    *,
    since: datetime,
    until: datetime,
    generated_by: str,
    company_name: str,
    confidential_label: str,
) -> ReportData:
    findings = await normalization_service.list_findings_created_between(
        session, since=since, until=until
    )
    events = await identity_service.list_audit_events(session, since=since, until=until)
    return ReportData(
        company_name=company_name,
        confidential_label=confidential_label,
        generated_by=generated_by,
        generated_at=datetime.now(UTC),
        since=since,
        until=until,
        summary=_summarize(findings),
        findings=findings,
        timeline=[_describe(event) for event in events],
    )
