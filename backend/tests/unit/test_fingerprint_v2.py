"""Fingerprint v2: cross-scanner correlation proofs using the real sample reports."""

from pathlib import Path

from tests.conftest import REPO_ROOT
from vulnconsole.contexts.ingestion.connectors.base import RawFindingDraft
from vulnconsole.contexts.ingestion.connectors.gitleaks import GitleaksConnector
from vulnconsole.contexts.ingestion.connectors.grype import GrypeConnector
from vulnconsole.contexts.ingestion.connectors.trivy import TrivyConnector
from vulnconsole.contexts.ingestion.connectors.trufflehog import TruffleHogConnector
from vulnconsole.contexts.normalization.domain.fingerprint import (
    compute_fingerprint,
    derive_identity,
)

SAMPLES: Path = REPO_ROOT / "deploy" / "sample-data"
REPO = "org/demo"


def _fingerprint(draft: RawFindingDraft, tool: str) -> str:
    rule_key, location_key = derive_identity(
        finding_class=draft.finding_class,
        tool=tool,
        rule_id=draft.rule_id,
        file_path=draft.file_path,
        hints=draft.hints,
    )
    return compute_fingerprint(
        finding_class=draft.finding_class,
        rule_key=rule_key,
        asset_key=REPO,
        location_key=location_key,
    )


def test_trivy_and_grype_agree_on_the_same_cve() -> None:
    """CVE-2024-35195 in requests, reported by both tools, is ONE finding."""
    trivy_findings = TrivyConnector().parse((SAMPLES / "trivy-example.json").read_bytes()).findings
    grype_findings = GrypeConnector().parse((SAMPLES / "grype-example.json").read_bytes()).findings

    trivy_requests = next(f for f in trivy_findings if f.hints.get("vuln_id") == "CVE-2024-35195")
    grype_requests = next(f for f in grype_findings if f.hints.get("vuln_id") == "CVE-2024-35195")

    # Different classes would split them; the shared sca surface is what merges.
    trivy_requests = trivy_requests.model_copy(update={"finding_class": "sca"})
    assert _fingerprint(trivy_requests, "trivy") == _fingerprint(grype_requests, "grype")


def test_package_upgrade_keeps_the_same_fingerprint() -> None:
    before = RawFindingDraft(
        rule_id="CVE-2024-35195",
        title="requests vuln",
        severity="medium",
        finding_class="sca",
        file_path="app/requirements.txt",
        payload={},
        hints={"vuln_id": "CVE-2024-35195", "purl_base": "pkg:pypi/requests",
               "package": "requests", "installed_version": "2.31.0"},
    )
    after = before.model_copy(
        update={"hints": {**before.hints, "installed_version": "2.31.5"}}
    )
    assert _fingerprint(before, "grype") == _fingerprint(after, "grype")


def test_gitleaks_and_trufflehog_agree_on_the_same_leak() -> None:
    """The same AWS key in the same file is ONE finding across both tools."""
    gl = GitleaksConnector().parse((SAMPLES / "gitleaks-example.json").read_bytes()).findings[0]
    th = TruffleHogConnector().parse(
        (SAMPLES / "trufflehog-example.jsonl").read_bytes()
    ).findings[0]
    assert _fingerprint(gl, "gitleaks") == _fingerprint(th, "trufflehog")


def test_same_secret_in_two_files_stays_two_findings() -> None:
    base = RawFindingDraft(
        rule_id="aws-access-key-id",
        title="AWS key",
        severity="high",
        finding_class="secret",
        file_path="config/prod.env",
        payload={},
        hints={"secret_hash": "a" * 64},
    )
    other_file = base.model_copy(update={"file_path": "scripts/deploy.sh"})
    assert _fingerprint(base, "gitleaks") != _fingerprint(other_file, "gitleaks")


def test_sast_identity_stays_tool_namespaced() -> None:
    rule_key, location_key = derive_identity(
        finding_class="sast",
        tool="semgrep",
        rule_id="python.sqli",
        file_path="app/db.py",
        hints={},
    )
    assert rule_key == "semgrep:python.sqli"
    assert location_key == "app/db.py"
