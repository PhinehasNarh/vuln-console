"""Grype JSON connector: dependency vulnerabilities with purl-precise artifacts."""

import json
from typing import Any

from vulnconsole.contexts.ingestion.connectors.base import (
    ConnectorError,
    FindingClass,
    ParseResult,
    RawFindingDraft,
    normalize_severity_name,
    purl_base,
)

# Grype artifact types that are OS/distro packages rather than app dependencies.
_OS_PACKAGE_TYPES = {"deb", "rpm", "apk", "rpmdb", "msrc-kb", "portage"}


class GrypeConnector:
    format_id = "grype-json"
    display_name = "Grype (JSON)"

    def sniff(self, artifact: bytes) -> bool:
        head = artifact[:4096].decode("utf-8", errors="replace")
        return '"matches"' in head and '"vulnerability"' in head

    def parse(self, artifact: bytes) -> ParseResult:
        try:
            document = json.loads(artifact)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ConnectorError(f"artifact is not valid JSON: {exc}") from exc
        if not isinstance(document, dict) or not isinstance(document.get("matches"), list):
            raise ConnectorError("artifact is not a Grype report: missing 'matches' list")

        findings: list[RawFindingDraft] = []
        for match in document["matches"]:
            if not isinstance(match, dict):
                continue
            findings.append(self._match(match))
        return ParseResult(tool_name="Grype", findings=findings)

    def _match(self, match: dict[str, Any]) -> RawFindingDraft:
        vuln: dict[str, Any] = match.get("vulnerability") or {}
        art: dict[str, Any] = match.get("artifact") or {}
        vuln_id = str(vuln.get("id") or "unknown")
        package = str(art.get("name") or "unknown")
        version = str(art.get("version") or "")
        finding_class: FindingClass = (
            "container" if art.get("type") in _OS_PACKAGE_TYPES else "sca"
        )

        locations = art.get("locations") or []
        file_path = None
        if locations and isinstance(locations[0], dict):
            file_path = locations[0].get("path")

        hints = {
            "vuln_id": vuln_id.upper(),
            "package": package,
            "installed_version": version,
        }
        base = purl_base(art.get("purl"))
        if base:
            hints["purl_base"] = base
        fix_versions = (vuln.get("fix") or {}).get("versions") or []
        if fix_versions:
            hints["fixed_version"] = str(fix_versions[0])

        description = str(vuln.get("description") or "")
        title = f"{vuln_id} in {package} {version}".strip()
        if description:
            title = f"{title}: {description}"

        return RawFindingDraft(
            rule_id=vuln_id[:300],
            title=title[:2000],
            severity=normalize_severity_name(vuln.get("severity")),
            finding_class=finding_class,
            file_path=file_path,
            line=None,
            payload=match,
            hints=hints,
        )
