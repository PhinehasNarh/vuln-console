from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT
from vulnconsole.contexts.ingestion.connectors.base import ConnectorError, purl_base
from vulnconsole.contexts.ingestion.connectors.grype import GrypeConnector
from vulnconsole.contexts.ingestion.connectors.trivy import TrivyConnector

SAMPLES: Path = REPO_ROOT / "deploy" / "sample-data"

trivy = TrivyConnector()
grype = GrypeConnector()


def test_purl_base_strips_version_and_qualifiers() -> None:
    assert purl_base("pkg:pypi/requests@2.31.0") == "pkg:pypi/requests"
    assert (
        purl_base("pkg:deb/debian/openssl@3.0.11-1~deb12u2?distro=debian-12.5")
        == "pkg:deb/debian/openssl"
    )
    assert purl_base("pkg:pypi/requests") == "pkg:pypi/requests"
    assert purl_base(None) is None


def test_trivy_parse_sample() -> None:
    result = trivy.parse((SAMPLES / "trivy-example.json").read_bytes())
    assert result.tool_name == "Trivy"
    assert len(result.findings) == 3

    zlib, openssl, requests_vuln = result.findings
    assert zlib.severity == "critical"
    assert zlib.finding_class == "container"  # os-pkgs in a container image
    assert zlib.hints["vuln_id"] == "CVE-2023-45853"
    assert zlib.hints["purl_base"] == "pkg:deb/debian/zlib1g"
    assert "fixed_version" not in zlib.hints  # empty FixedVersion is omitted

    assert openssl.hints["fixed_version"] == "3.0.14-1~deb12u2"
    # A language dependency (pip) is SCA even inside a container image, so it
    # correlates with a Grype directory scan of the same package.
    assert requests_vuln.severity == "medium"
    assert requests_vuln.finding_class == "sca"
    assert requests_vuln.hints["purl_base"] == "pkg:pypi/requests"


def test_trivy_sniffs_only_trivy() -> None:
    assert trivy.sniff((SAMPLES / "trivy-example.json").read_bytes())
    assert not trivy.sniff((SAMPLES / "grype-example.json").read_bytes())
    assert not trivy.sniff((SAMPLES / "semgrep-example.sarif").read_bytes())


def test_grype_parse_sample() -> None:
    result = grype.parse((SAMPLES / "grype-example.json").read_bytes())
    assert result.tool_name == "Grype"
    assert len(result.findings) == 2

    requests_vuln, flask_cors = result.findings
    assert requests_vuln.severity == "medium"
    assert requests_vuln.finding_class == "sca"  # python artifact type
    assert requests_vuln.hints["vuln_id"] == "CVE-2024-35195"
    assert requests_vuln.hints["purl_base"] == "pkg:pypi/requests"
    assert requests_vuln.hints["fixed_version"] == "2.32.0"
    assert requests_vuln.file_path == "app/requirements.txt"

    assert flask_cors.severity == "high"
    assert flask_cors.hints["vuln_id"] == "GHSA-56PW-MPJ4-FXWW"


def test_grype_sniffs_only_grype() -> None:
    assert grype.sniff((SAMPLES / "grype-example.json").read_bytes())
    assert not grype.sniff((SAMPLES / "trivy-example.json").read_bytes())


def test_both_reject_garbage() -> None:
    for connector in (trivy, grype):
        with pytest.raises(ConnectorError):
            connector.parse(b"not json")
        with pytest.raises(ConnectorError):
            connector.parse(b'{"unrelated": true}')
