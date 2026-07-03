"""Remediation SLA policy: time-to-fix targets per severity.

Kept pure (no I/O) so it is trivially testable. Durations come from settings so
an operator can tune them without code changes.
"""

from datetime import datetime, timedelta
from typing import Literal

from vulnconsole.shared.config import get_settings

SlaStatus = Literal["on_track", "due_soon", "overdue", "none"]

# Finding lifecycle states that are still the owner's responsibility to close.
OPEN_STATUSES: frozenset[str] = frozenset({"new", "triaged", "in_remediation", "reopened"})

DUE_SOON_WINDOW = timedelta(days=2)


def sla_days_for(severity: str) -> int | None:
    settings = get_settings()
    return {
        "critical": settings.sla_days_critical,
        "high": settings.sla_days_high,
        "medium": settings.sla_days_medium,
        "low": settings.sla_days_low,
    }.get(severity)


def compute_due_at(first_seen: datetime, severity: str) -> datetime | None:
    days = sla_days_for(severity)
    if days is None:
        return None
    return first_seen + timedelta(days=days)


def sla_status(due_at: datetime | None, status: str, now: datetime) -> SlaStatus:
    if due_at is None or status not in OPEN_STATUSES:
        return "none"
    if now >= due_at:
        return "overdue"
    if due_at - now <= DUE_SOON_WINDOW:
        return "due_soon"
    return "on_track"


def is_open(status: str) -> bool:
    return status in OPEN_STATUSES
