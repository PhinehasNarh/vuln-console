"""Connector protocol and registry (ADR-0008)."""

from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low", "info"]
FindingClass = Literal["sast", "sca", "secret", "iac", "container", "dast"]


class RawFindingDraft(BaseModel):
    rule_id: str = Field(max_length=300)
    title: str
    severity: Severity
    finding_class: FindingClass
    file_path: str | None = None
    line: int | None = None
    payload: dict[str, Any]
    # Correlation hints consumed by fingerprint v2 (ADR-0007): standard keys are
    # vuln_id, purl_base, package, installed_version, fixed_version, secret_hash.
    hints: dict[str, str] = Field(default_factory=dict)


class ParseResult(BaseModel):
    tool_name: str | None
    findings: list[RawFindingDraft]


class ConnectorError(Exception):
    """Raised when an artifact claims a format but cannot be parsed as it."""


@runtime_checkable
class Connector(Protocol):
    format_id: str
    display_name: str

    def sniff(self, artifact: bytes) -> bool: ...

    def parse(self, artifact: bytes) -> ParseResult: ...


_REGISTRY: dict[str, Connector] = {}


def register(connector: Connector) -> None:
    _REGISTRY[connector.format_id] = connector


def get_connector(format_id: str) -> Connector | None:
    return _REGISTRY.get(format_id)


def sniff_format(artifact: bytes) -> Connector | None:
    for connector in _REGISTRY.values():
        if connector.sniff(artifact):
            return connector
    return None


def supported_formats() -> list[str]:
    return sorted(_REGISTRY)


# ---- shared helpers for connectors ----

_NAME_SEVERITY: dict[str, Severity] = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "moderate": "medium",
    "low": "low",
    "negligible": "info",
    "unknown": "info",
    "info": "info",
}


def normalize_severity_name(value: str | None, default: Severity = "info") -> Severity:
    if not value:
        return default
    return _NAME_SEVERITY.get(value.strip().lower(), default)


def purl_base(purl: str | None) -> str | None:
    """Strip version and qualifiers from a package URL.

    pkg:pypi/requests@2.31.0?arch=any -> pkg:pypi/requests, so an upgrade that
    still carries the CVE does not mint a new finding (ADR-0007).
    """
    if not purl:
        return None
    without_qualifiers = purl.split("?", 1)[0]
    base, at, _version = without_qualifiers.rpartition("@")
    return base if at else without_qualifiers


def hash_secret(value: str) -> str:
    """Stable hash of a secret value for cross-scanner correlation.

    Unsalted on purpose: the same leaked credential must produce the same hash
    across scans and scanners. Only high-entropy secret material is hashed, and
    access to secret findings is RBAC-gated (threat model).
    """
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


REDACTED = "[REDACTED]"
