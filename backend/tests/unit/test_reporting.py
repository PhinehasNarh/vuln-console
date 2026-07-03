import uuid
from datetime import UTC, datetime

from vulnconsole.contexts.identity.application.schemas import AuditEventOut
from vulnconsole.contexts.normalization.application.schemas import FindingOut
from vulnconsole.contexts.reporting.application.report import (
    ReportData,
    ReportSummary,
    _describe,
    _summarize,
)
from vulnconsole.contexts.reporting.infrastructure.logo import logo_data_uri, monogram
from vulnconsole.contexts.reporting.infrastructure.render import render_html

NOW = datetime(2026, 7, 3, 12, 0, tzinfo=UTC)


def _finding(
    severity: str, *, owner: str | None = None, sla: str = "none", title: str = "x"
) -> FindingOut:
    return FindingOut(
        id=uuid.uuid4(),
        fingerprint="f" * 64,
        finding_class="sca",
        rule_key="CVE-2024-0001",
        title=title,
        severity=severity,
        status="new",
        repository="acme/app",
        file_path=None,
        line=None,
        package="requests@2.31.0",
        cve_id="CVE-2024-0001",
        fixed_version="2.32.0",
        tool_names=["trivy"],
        owner=owner,
        assigned_at=None,
        sla_due_at=None,
        sla_status=sla,  # type: ignore[arg-type]
        first_seen=NOW,
        last_seen=NOW,
    )


def _audit(action: str, detail: dict[str, object], actor: str = "user:1") -> AuditEventOut:
    return AuditEventOut(
        actor=actor,
        action=action,
        entity_type="finding",
        entity_id="abc",
        detail=detail,
        created_at=NOW,
    )


def test_monogram() -> None:
    assert monogram("Acme Security Corp") == "AS"
    assert monogram("Globex") == "GL"
    assert monogram("") == "VC"


def test_logo_data_uri_missing_returns_none() -> None:
    assert logo_data_uri("") is None
    assert logo_data_uri("/no/such/file.png") is None


def test_logo_data_uri_inlines_file(tmp_path) -> None:
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"\x89PNG\r\n\x1a\n fake bytes")
    uri = logo_data_uri(str(logo))
    assert uri is not None
    assert uri.startswith("data:image/png;base64,")


def test_summarize_counts() -> None:
    findings = [
        _finding("critical", owner="sana", sla="overdue"),
        _finding("high", sla="on_track"),
        _finding("high", owner="marco"),
    ]
    summary = _summarize(findings)
    assert summary.total_findings == 3
    assert summary.by_severity["high"] == 2
    assert summary.by_severity["critical"] == 1
    assert summary.overdue == 1
    assert summary.assigned == 2
    assert summary.unassigned == 1
    assert summary.repositories == 1


def test_describe_maps_known_actions() -> None:
    assigned = _describe(_audit("finding.assigned", {"to": "marco"}))
    assert assigned.category == "triage"
    assert "marco" in assigned.summary

    scan = _describe(_audit("scan.created", {"repository": "acme/app"}))
    assert "acme/app" in scan.summary

    denied = _describe(_audit("authz.denied", {"permission": "users:manage"}))
    assert denied.category == "security"
    assert "users:manage" in denied.summary


def test_describe_falls_back_for_unknown_action() -> None:
    event = _describe(_audit("weird.thing.happened", {}))
    assert event.category == "event"
    assert event.summary == "weird thing happened"


def _report(
    findings: list[FindingOut], timeline_actions: list[tuple[str, dict[str, object]]]
) -> ReportData:
    return ReportData(
        company_name="Acme <Security>",  # includes chars that must be escaped
        confidential_label="CONFIDENTIAL",
        generated_by="sana@example.com",
        generated_at=NOW,
        since=datetime(2026, 6, 1, tzinfo=UTC),
        until=NOW,
        summary=_summarize(findings),
        findings=findings,
        timeline=[_describe(_audit(a, d)) for a, d in timeline_actions],
    )


def test_render_is_self_contained_and_branded() -> None:
    data = _report(
        [_finding("critical", owner="sana", sla="overdue", title="Public S3 bucket")],
        [("scan.created", {"repository": "acme/app"}), ("finding.assigned", {"to": "sana"})],
    )
    html = render_html(data, None)
    assert html.startswith("<!doctype html>")
    assert "CONFIDENTIAL" in html
    assert "Security Audit Report" in html
    assert "Public S3 bucket" in html
    assert "sana@example.com" in html
    assert "Incident timeline" in html
    # monogram fallback because no logo provided
    assert 'class="logo monogram"' in html
    # no external resource references (fully self-contained)
    assert "http://" not in html and "https://" not in html


def test_render_escapes_untrusted_text() -> None:
    data = _report([_finding("high", title="<script>alert(1)</script>")], [])
    html = render_html(data, None)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    # company name angle brackets are escaped too
    assert "Acme <Security>" not in html
    assert "Acme &lt;Security&gt;" in html


def test_render_with_logo_uses_img() -> None:
    data = _report([_finding("low")], [])
    html = render_html(data, "data:image/png;base64,AAAA")
    assert 'class="logo" src="data:image/png;base64,AAAA"' in html


def test_empty_report_still_renders() -> None:
    data = ReportData(
        company_name="Globex",
        confidential_label="CONFIDENTIAL",
        generated_by="ops",
        generated_at=NOW,
        since=datetime(2026, 6, 1, tzinfo=UTC),
        until=NOW,
        summary=ReportSummary(
            total_findings=0,
            by_severity={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
            overdue=0,
            assigned=0,
            unassigned=0,
            repositories=0,
        ),
        findings=[],
        timeline=[],
    )
    html = render_html(data, None)
    assert "No findings in this period." in html
    assert "No recorded activity in this period." in html
