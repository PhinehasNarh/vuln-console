from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT
from vulnconsole.contexts.ingestion.connectors.base import ConnectorError
from vulnconsole.contexts.ingestion.connectors.prowler import ProwlerConnector
from vulnconsole.contexts.normalization.domain.fingerprint import (
    compute_fingerprint,
    derive_identity,
)

SAMPLES: Path = REPO_ROOT / "deploy" / "sample-data"
prowler = ProwlerConnector()


def test_sniff_accepts_prowler_ocsf() -> None:
    assert prowler.sniff((SAMPLES / "prowler-example.json").read_bytes())


def test_sniff_rejects_other_scanners() -> None:
    for other in ("trivy-example.json", "grype-example.json", "gitleaks-example.json"):
        assert not prowler.sniff((SAMPLES / other).read_bytes())


def test_parse_ocsf_sample_filters_pass_and_maps_fields() -> None:
    result = prowler.parse((SAMPLES / "prowler-example.json").read_bytes())
    assert result.tool_name == "Prowler"
    # 4 checks in the sample, but the PASS one is not a finding.
    assert len(result.findings) == 3

    s3, root_mfa, azure = result.findings

    assert s3.finding_class == "cloud"
    assert s3.severity == "critical"
    assert s3.rule_id == "s3_bucket_public_access"
    assert s3.file_path == "arn:aws:s3:::acme-prod-assets"
    assert s3.hints["provider"] == "aws"
    assert s3.hints["account"] == "123456789012"
    assert s3.hints["region"] == "us-east-1"
    assert s3.hints["resource_uid"] == "arn:aws:s3:::acme-prod-assets"

    assert root_mfa.severity == "high"

    # Azure and AWS both land in the same 'cloud' class and view.
    assert azure.finding_class == "cloud"
    assert azure.hints["provider"] == "azure"
    assert azure.hints["account"] == "9f2c1e8a-4b3d-4a1f-8c2e-1234567890ab"
    assert azure.file_path.startswith("/subscriptions/")


def test_pass_findings_are_excluded() -> None:
    result = prowler.parse((SAMPLES / "prowler-example.json").read_bytes())
    titles = [f.title for f in result.findings]
    assert all("EBS default encryption" not in t for t in titles)


def test_native_v3_format_fallback() -> None:
    native = b"""[
      {
        "Provider": "aws",
        "CheckID": "iam_user_mfa_enabled_console_access",
        "CheckTitle": "Ensure MFA is enabled for IAM users with console access",
        "Severity": "high",
        "Status": "FAIL",
        "AccountId": "210987654321",
        "Region": "us-west-2",
        "ResourceId": "alice",
        "ResourceArn": "arn:aws:iam::210987654321:user/alice",
        "ResourceType": "AwsIamUser"
      },
      {
        "CheckID": "iam_password_policy_minimum_length_14",
        "Status": "PASS",
        "Severity": "medium",
        "AccountId": "210987654321"
      }
    ]"""
    result = prowler.parse(native)
    assert result.tool_name == "Prowler"
    assert len(result.findings) == 1  # PASS excluded
    finding = result.findings[0]
    assert finding.finding_class == "cloud"
    assert finding.severity == "high"
    assert finding.rule_id == "iam_user_mfa_enabled_console_access"
    assert finding.file_path == "arn:aws:iam::210987654321:user/alice"
    assert finding.hints["provider"] == "aws"


def test_same_check_same_resource_correlates_across_rescans() -> None:
    findings = prowler.parse((SAMPLES / "prowler-example.json").read_bytes()).findings
    s3 = findings[0]

    def fp(draft):
        rule_key, location_key = derive_identity(
            finding_class=draft.finding_class,
            tool="prowler",
            rule_id=draft.rule_id,
            file_path=draft.file_path,
            hints=draft.hints,
        )
        return compute_fingerprint(
            finding_class=draft.finding_class,
            rule_key=rule_key,
            asset_key="acme/aws",
            location_key=location_key,
        )

    # Re-parsing the same report yields the same fingerprint (idempotent dedup),
    # and identity is the check id on the resource, not the tool.
    assert fp(s3) == fp(s3)
    rule_key, location_key = derive_identity(
        finding_class="cloud",
        tool="prowler",
        rule_id=s3.rule_id,
        file_path=s3.file_path,
        hints=s3.hints,
    )
    assert rule_key == "s3_bucket_public_access"
    assert location_key == "arn:aws:s3:::acme-prod-assets"


def test_rejects_garbage() -> None:
    with pytest.raises(ConnectorError):
        prowler.parse(b"not json")
    with pytest.raises(ConnectorError):
        prowler.parse(b'{"not": "a list"}')
    with pytest.raises(ConnectorError):
        prowler.parse(b"[]")
