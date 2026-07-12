"""Message composition for notifiable events.

FindingRef is the notifications context's own input type, so this context never
imports another context's models (ADR-0002). Composition roots map their
domain objects onto it.
"""

from pydantic import BaseModel

from vulnconsole.shared.config import get_settings

SEVERITY_EMOJI = {
    "critical": "\U0001f534",  # red circle
    "high": "\U0001f7e0",  # orange circle
    "medium": "\U0001f7e1",  # yellow circle
    "low": "\U0001f7e2",  # green circle
    "info": "\U0001f535",  # blue circle
}


class FindingRef(BaseModel):
    id: str
    title: str
    severity: str
    repository: str
    owner: str | None = None


class Message(BaseModel):
    event: str
    subject: str
    body: str
    finding_id: str
    link: str


def _link(finding_id: str) -> str:
    base = get_settings().notifications_base_url.rstrip("/")
    return f"{base}/findings/{finding_id}"


def build_assignment(finding: FindingRef) -> Message:
    emoji = SEVERITY_EMOJI.get(finding.severity, "")
    subject = f"Finding assigned to {finding.owner}: {finding.title}"
    body = (
        f"{emoji} {finding.severity.upper()} finding in {finding.repository} "
        f"was assigned to {finding.owner}.\n\n{finding.title}"
    )
    return Message(
        event="finding.assigned",
        subject=subject,
        body=body,
        finding_id=finding.id,
        link=_link(finding.id),
    )


def build_status_change(finding: FindingRef, status: str, reason: str) -> Message:
    emoji = SEVERITY_EMOJI.get(finding.severity, "")
    pretty = status.replace("_", " ")
    subject = f"Finding marked {pretty}: {finding.title}"
    body = (
        f"{emoji} A {finding.severity.upper()} finding in {finding.repository} "
        f"was marked {pretty}.\nReason: {reason}\n\n{finding.title}"
    )
    return Message(
        event="finding.status_changed",
        subject=subject,
        body=body,
        finding_id=finding.id,
        link=_link(finding.id),
    )


def build_sla_breach(finding: FindingRef, due_at: str | None) -> Message:
    emoji = SEVERITY_EMOJI.get(finding.severity, "")
    owner = finding.owner or "unassigned"
    subject = f"SLA breached ({finding.severity}): {finding.title}"
    body = (
        f"{emoji} SLA breached for a {finding.severity.upper()} finding in "
        f"{finding.repository}.\nOwner: {owner}. Due: {due_at or 'n/a'}.\n\n{finding.title}"
    )
    return Message(
        event="sla.breached",
        subject=subject,
        body=body,
        finding_id=finding.id,
        link=_link(finding.id),
    )
