"""Finding lifecycle state machine (pure).

Defines which status transitions are legal and which require extra data. The
application layer calls these helpers and raises the HTTP-facing errors, so this
module stays free of transport concerns and is trivially testable.
"""

from vulnconsole.contexts.normalization.domain.models import FINDING_STATUSES

# Dispositions that close a finding (they leave the SLA clock, per sla.py).
CLOSED_STATUSES: frozenset[str] = frozenset(
    {"fixed", "risk_accepted", "false_positive", "suppressed"}
)

_WORKING = {"triaged", "in_remediation", "fixed", "false_positive", "risk_accepted", "suppressed"}

# Legal target statuses from each current status.
_ALLOWED: dict[str, frozenset[str]] = {
    "new": frozenset(_WORKING),
    "triaged": frozenset(_WORKING - {"triaged"} | {"new"}),
    "in_remediation": frozenset(_WORKING - {"in_remediation"} | {"triaged"}),
    "reopened": frozenset(_WORKING),
    # Closed findings can only be reopened.
    "fixed": frozenset({"reopened"}),
    "risk_accepted": frozenset({"reopened"}),
    "false_positive": frozenset({"reopened"}),
    "suppressed": frozenset({"reopened"}),
}

# Transitions worth notifying a channel about (the rest are routine progress).
NOTIFIABLE_STATUSES: frozenset[str] = frozenset(
    {"risk_accepted", "false_positive", "suppressed", "reopened"}
)


def is_valid_status(status: str) -> bool:
    return status in FINDING_STATUSES


def allowed_transitions(current: str) -> tuple[str, ...]:
    return tuple(sorted(_ALLOWED.get(current, frozenset())))


def is_allowed(current: str, target: str) -> bool:
    return target in _ALLOWED.get(current, frozenset())


def requires_expiry(target: str) -> bool:
    return target == "risk_accepted"
