from vulnconsole.contexts.normalization.domain.triage import (
    CLOSED_STATUSES,
    NOTIFIABLE_STATUSES,
    allowed_transitions,
    is_allowed,
    is_valid_status,
    requires_expiry,
)


def test_valid_status() -> None:
    assert is_valid_status("risk_accepted")
    assert not is_valid_status("banana")


def test_open_finding_can_be_dispositioned() -> None:
    targets = set(allowed_transitions("new"))
    assert {"triaged", "in_remediation", "fixed", "false_positive", "risk_accepted"} <= targets
    # never a no-op transition to itself
    assert "new" not in targets


def test_closed_findings_only_reopen() -> None:
    for status in CLOSED_STATUSES:
        assert allowed_transitions(status) == ("reopened",)


def test_is_allowed_matrix() -> None:
    assert is_allowed("new", "risk_accepted")
    assert is_allowed("risk_accepted", "reopened")
    assert not is_allowed("risk_accepted", "fixed")  # must reopen first
    assert not is_allowed("fixed", "fixed")
    assert not is_allowed("new", "new")


def test_only_risk_acceptance_requires_expiry() -> None:
    assert requires_expiry("risk_accepted")
    assert not requires_expiry("false_positive")
    assert not requires_expiry("fixed")


def test_notifiable_statuses() -> None:
    assert "risk_accepted" in NOTIFIABLE_STATUSES
    assert "false_positive" in NOTIFIABLE_STATUSES
    assert "reopened" in NOTIFIABLE_STATUSES
    # routine progress does not notify
    assert "triaged" not in NOTIFIABLE_STATUSES
    assert "in_remediation" not in NOTIFIABLE_STATUSES
    assert "fixed" not in NOTIFIABLE_STATUSES


def test_reopened_can_be_worked_again() -> None:
    targets = set(allowed_transitions("reopened"))
    assert "in_remediation" in targets
    assert "fixed" in targets
