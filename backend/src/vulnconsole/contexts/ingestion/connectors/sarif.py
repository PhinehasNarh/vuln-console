"""SARIF 2.1.0 connector. Covers every tool that exports SARIF (Semgrep, CodeQL, ...)."""

import json
from typing import Any

from vulnconsole.contexts.ingestion.connectors.base import (
    ConnectorError,
    ParseResult,
    RawFindingDraft,
    Severity,
)

_LEVEL_SEVERITY: dict[str, Severity] = {
    "error": "high",
    "warning": "medium",
    "note": "low",
    "none": "info",
}


def _severity_from_score(score: float) -> Severity:
    if score >= 9.0:
        return "critical"
    if score >= 7.0:
        return "high"
    if score >= 4.0:
        return "medium"
    if score > 0.0:
        return "low"
    return "info"


def _security_severity(*properties: dict[str, Any] | None) -> Severity | None:
    for props in properties:
        if not props:
            continue
        raw = props.get("security-severity")
        if raw is None:
            continue
        try:
            return _severity_from_score(float(raw))
        except (TypeError, ValueError):
            continue
    return None


class SarifConnector:
    format_id = "sarif"
    display_name = "SARIF 2.1.0"

    def sniff(self, artifact: bytes) -> bool:
        head = artifact[:4096].decode("utf-8", errors="replace")
        return '"runs"' in head and ('"sarif' in head or '"version"' in head)

    def parse(self, artifact: bytes) -> ParseResult:
        try:
            document = json.loads(artifact)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ConnectorError(f"artifact is not valid JSON: {exc}") from exc
        if not isinstance(document, dict) or not isinstance(document.get("runs"), list):
            raise ConnectorError("artifact is not a SARIF document: missing 'runs' list")

        tool_name: str | None = None
        findings: list[RawFindingDraft] = []
        for run in document["runs"]:
            if not isinstance(run, dict):
                continue
            driver = (run.get("tool") or {}).get("driver") or {}
            run_tool = driver.get("name")
            tool_name = tool_name or run_tool
            rules_by_id = {
                rule["id"]: rule
                for rule in driver.get("rules") or []
                if isinstance(rule, dict) and "id" in rule
            }
            for result in run.get("results") or []:
                if not isinstance(result, dict):
                    continue
                findings.append(self._to_draft(result, rules_by_id))
        return ParseResult(tool_name=tool_name, findings=findings)

    def _to_draft(
        self, result: dict[str, Any], rules_by_id: dict[str, dict[str, Any]]
    ) -> RawFindingDraft:
        rule_id = result.get("ruleId") or (result.get("rule") or {}).get("id") or "unknown"
        rule = rules_by_id.get(rule_id, {})

        severity = _security_severity(result.get("properties"), rule.get("properties"))
        if severity is None:
            level = result.get("level") or rule.get("defaultConfiguration", {}).get(
                "level", "warning"
            )
            severity = _LEVEL_SEVERITY.get(str(level), "medium")

        title = (
            (result.get("message") or {}).get("text")
            or (rule.get("shortDescription") or {}).get("text")
            or rule_id
        )

        file_path: str | None = None
        line: int | None = None
        locations = result.get("locations") or []
        if locations and isinstance(locations[0], dict):
            physical = locations[0].get("physicalLocation") or {}
            file_path = (physical.get("artifactLocation") or {}).get("uri")
            region_line = (physical.get("region") or {}).get("startLine")
            line = region_line if isinstance(region_line, int) else None

        return RawFindingDraft(
            rule_id=str(rule_id)[:300],
            title=str(title)[:2000],
            severity=severity,
            finding_class="sast",
            file_path=file_path,
            line=line,
            payload=result,
        )
