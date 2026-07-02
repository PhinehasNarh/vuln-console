import pytest

from tests.conftest import SAMPLE_SARIF
from vulnconsole.contexts.ingestion.connectors.base import ConnectorError
from vulnconsole.contexts.ingestion.connectors.sarif import SarifConnector

connector = SarifConnector()


def test_sniff_accepts_sarif() -> None:
    assert connector.sniff(SAMPLE_SARIF.read_bytes())


def test_sniff_rejects_other_content() -> None:
    assert not connector.sniff(b'{"foo": "bar"}')
    assert not connector.sniff(b"\x00\x01binary")


def test_parse_sample() -> None:
    result = connector.parse(SAMPLE_SARIF.read_bytes())
    assert result.tool_name == "Semgrep"
    assert len(result.findings) == 3

    sqli_one, sqli_two, secret = result.findings
    # security-severity 9.8 on the rule outranks the level mapping
    assert sqli_one.severity == "critical"
    assert sqli_one.rule_id == "python.lang.security.sqlalchemy-sql-injection"
    assert sqli_one.file_path == "app/db.py"
    assert sqli_one.line == 10
    assert sqli_two.line == 42
    # no security-severity: level "warning" maps to medium
    assert secret.severity == "medium"
    assert secret.file_path == "app/config.py"


def test_parse_rejects_invalid_json() -> None:
    with pytest.raises(ConnectorError):
        connector.parse(b"not json at all")


def test_parse_rejects_non_sarif_json() -> None:
    with pytest.raises(ConnectorError):
        connector.parse(b'{"version": "2.1.0"}')
