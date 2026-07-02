import json
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT
from vulnconsole.contexts.ingestion.connectors.base import REDACTED, ConnectorError
from vulnconsole.contexts.ingestion.connectors.gitleaks import GitleaksConnector
from vulnconsole.contexts.ingestion.connectors.trufflehog import TruffleHogConnector

SAMPLES: Path = REPO_ROOT / "deploy" / "sample-data"
AWS_KEY = "AKIAIOSFODNN7EXAMPLE"  # the plaintext planted in both sample reports

gitleaks = GitleaksConnector()
trufflehog = TruffleHogConnector()


def test_gitleaks_parse_and_redaction() -> None:
    result = gitleaks.parse((SAMPLES / "gitleaks-example.json").read_bytes())
    assert result.tool_name == "Gitleaks"
    assert len(result.findings) == 2

    aws = result.findings[0]
    assert aws.finding_class == "secret"
    assert aws.severity == "high"
    assert aws.file_path == "config/prod.env"
    assert aws.line == 12
    assert aws.hints["secret_hash"]

    # The secret value must not survive anywhere in what gets persisted.
    for draft in result.findings:
        serialized = json.dumps(draft.payload) + draft.title
        assert AWS_KEY not in serialized
        assert "sk_live_" not in serialized
        assert draft.payload["Secret"] == REDACTED
        assert draft.payload["Match"] == REDACTED


def test_trufflehog_parse_verified_severity_and_redaction() -> None:
    result = trufflehog.parse((SAMPLES / "trufflehog-example.jsonl").read_bytes())
    assert result.tool_name == "TruffleHog"
    assert len(result.findings) == 2

    verified, unverified = result.findings
    assert verified.severity == "critical"  # Verified: true
    assert unverified.severity == "high"
    assert verified.file_path == "config/prod.env"
    assert verified.line == 12

    for draft in result.findings:
        serialized = json.dumps(draft.payload) + draft.title
        assert AWS_KEY not in serialized
        assert "ghp_Test" not in serialized
        assert draft.payload["Raw"] == REDACTED


def test_same_secret_hashes_identically_across_scanners() -> None:
    gl = gitleaks.parse((SAMPLES / "gitleaks-example.json").read_bytes()).findings[0]
    th = trufflehog.parse((SAMPLES / "trufflehog-example.jsonl").read_bytes()).findings[0]
    assert gl.hints["secret_hash"] == th.hints["secret_hash"]


def test_sniffing_is_mutually_exclusive() -> None:
    gitleaks_bytes = (SAMPLES / "gitleaks-example.json").read_bytes()
    trufflehog_bytes = (SAMPLES / "trufflehog-example.jsonl").read_bytes()
    assert gitleaks.sniff(gitleaks_bytes)
    assert not gitleaks.sniff(trufflehog_bytes)
    assert trufflehog.sniff(trufflehog_bytes)
    assert not trufflehog.sniff(gitleaks_bytes)


def test_rejects_garbage() -> None:
    with pytest.raises(ConnectorError):
        gitleaks.parse(b"{}")
    with pytest.raises(ConnectorError):
        trufflehog.parse(b'{"no": "detector"}')
