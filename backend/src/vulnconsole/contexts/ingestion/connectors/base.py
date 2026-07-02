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
