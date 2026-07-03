from datetime import UTC, datetime, timedelta

from vulnconsole.contexts.normalization.domain.sla import (
    compute_due_at,
    is_open,
    sla_days_for,
    sla_status,
)

FIRST_SEEN = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)


def test_sla_days_per_severity() -> None:
    assert sla_days_for("critical") == 3
    assert sla_days_for("high") == 7
    assert sla_days_for("medium") == 30
    assert sla_days_for("low") == 90
    assert sla_days_for("info") is None


def test_compute_due_at() -> None:
    assert compute_due_at(FIRST_SEEN, "critical") == FIRST_SEEN + timedelta(days=3)
    assert compute_due_at(FIRST_SEEN, "info") is None


def test_sla_status_transitions() -> None:
    due = FIRST_SEEN + timedelta(days=7)
    # comfortably before due
    assert sla_status(due, "new", FIRST_SEEN) == "on_track"
    # within the 2-day due-soon window
    assert sla_status(due, "new", due - timedelta(hours=12)) == "due_soon"
    # past due
    assert sla_status(due, "new", due + timedelta(hours=1)) == "overdue"


def test_closed_findings_have_no_sla_pressure() -> None:
    due = FIRST_SEEN + timedelta(days=1)
    late = due + timedelta(days=5)
    for closed in ("fixed", "risk_accepted", "false_positive", "suppressed"):
        assert sla_status(due, closed, late) == "none"


def test_no_due_date_is_none() -> None:
    assert sla_status(None, "new", FIRST_SEEN) == "none"


def test_is_open() -> None:
    assert is_open("new")
    assert is_open("in_remediation")
    assert not is_open("fixed")
    assert not is_open("risk_accepted")
