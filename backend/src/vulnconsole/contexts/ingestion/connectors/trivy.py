"""Trivy native JSON connector (schema version 2): OS and language package
vulnerabilities, misconfigurations, and secrets from one report."""

import json
from typing import Any

from vulnconsole.contexts.ingestion.connectors.base import (
    REDACTED,
    ConnectorError,
    FindingClass,
    ParseResult,
    RawFindingDraft,
    hash_secret,
    normalize_severity_name,
    purl_base,
)


class TrivyConnector:
    format_id = "trivy-json"
    display_name = "Trivy (native JSON)"

    def sniff(self, artifact: bytes) -> bool:
        head = artifact[:4096].decode("utf-8", errors="replace")
        return '"SchemaVersion"' in head and '"ArtifactName"' in head

    def parse(self, artifact: bytes) -> ParseResult:
        try:
            document = json.loads(artifact)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ConnectorError(f"artifact is not valid JSON: {exc}") from exc
        if not isinstance(document, dict) or not isinstance(document.get("Results"), list):
            raise ConnectorError("artifact is not a Trivy report: missing 'Results' list")

        artifact_type = document.get("ArtifactType", "")
        vuln_class: FindingClass = "container" if artifact_type == "container_image" else "sca"

        findings: list[RawFindingDraft] = []
        for result in document["Results"]:
            if not isinstance(result, dict):
                continue
            target = str(result.get("Target") or "")
            for vuln in result.get("Vulnerabilities") or []:
                findings.append(self._vulnerability(vuln, target, vuln_class))
            for misconfig in result.get("Misconfigurations") or []:
                findings.append(self._misconfiguration(misconfig, target))
            for secret in result.get("Secrets") or []:
                findings.append(self._secret(secret, target))
        return ParseResult(tool_name="Trivy", findings=findings)

    def _vulnerability(
        self, vuln: dict[str, Any], target: str, finding_class: FindingClass
    ) -> RawFindingDraft:
        vuln_id = str(vuln.get("VulnerabilityID") or "unknown")
        package = str(vuln.get("PkgName") or "unknown")
        installed = str(vuln.get("InstalledVersion") or "")
        purl = (vuln.get("PkgIdentifier") or {}).get("PURL")
        hints = {
            "vuln_id": vuln_id.upper(),
            "package": package,
            "installed_version": installed,
        }
        base = purl_base(purl)
        if base:
            hints["purl_base"] = base
        if vuln.get("FixedVersion"):
            hints["fixed_version"] = str(vuln["FixedVersion"])
        return RawFindingDraft(
            rule_id=vuln_id[:300],
            title=str(vuln.get("Title") or f"{vuln_id} in {package}")[:2000],
            severity=normalize_severity_name(vuln.get("Severity")),
            finding_class=finding_class,
            file_path=target or None,
            line=None,
            payload=vuln,
            hints=hints,
        )

    def _misconfiguration(self, misconfig: dict[str, Any], target: str) -> RawFindingDraft:
        rule = str(misconfig.get("ID") or "unknown")
        start_line = ((misconfig.get("CauseMetadata") or {}).get("StartLine"))
        return RawFindingDraft(
            rule_id=rule[:300],
            title=str(misconfig.get("Title") or misconfig.get("Description") or rule)[:2000],
            severity=normalize_severity_name(misconfig.get("Severity")),
            finding_class="iac",
            file_path=target or None,
            line=start_line if isinstance(start_line, int) else None,
            payload=misconfig,
        )

    def _secret(self, secret: dict[str, Any], target: str) -> RawFindingDraft:
        payload = dict(secret)
        match_value = str(payload.get("Match") or "")
        payload["Match"] = REDACTED
        start_line = payload.get("StartLine")
        hints = {}
        if match_value:
            hints["secret_hash"] = hash_secret(match_value)
        return RawFindingDraft(
            rule_id=str(secret.get("RuleID") or "secret")[:300],
            title=str(secret.get("Title") or "Secret detected")[:2000],
            severity=normalize_severity_name(secret.get("Severity"), default="high"),
            finding_class="secret",
            file_path=target or None,
            line=start_line if isinstance(start_line, int) else None,
            payload=payload,
            hints=hints,
        )
