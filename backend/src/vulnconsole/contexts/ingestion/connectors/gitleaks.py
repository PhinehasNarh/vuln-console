"""Gitleaks JSON connector. Secret values are hashed for correlation and
redacted before anything is persisted; the plaintext never leaves the parser."""

import json
from typing import Any

from vulnconsole.contexts.ingestion.connectors.base import (
    REDACTED,
    ConnectorError,
    ParseResult,
    RawFindingDraft,
    hash_secret,
)


class GitleaksConnector:
    format_id = "gitleaks-json"
    display_name = "Gitleaks (JSON)"

    def sniff(self, artifact: bytes) -> bool:
        head = artifact[:4096].decode("utf-8", errors="replace").lstrip()
        return head.startswith("[") and '"RuleID"' in head

    def parse(self, artifact: bytes) -> ParseResult:
        try:
            document = json.loads(artifact)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ConnectorError(f"artifact is not valid JSON: {exc}") from exc
        if not isinstance(document, list):
            raise ConnectorError("artifact is not a Gitleaks report: expected a JSON array")

        findings: list[RawFindingDraft] = []
        for leak in document:
            if not isinstance(leak, dict) or "RuleID" not in leak:
                continue
            findings.append(self._leak(leak))
        return ParseResult(tool_name="Gitleaks", findings=findings)

    def _leak(self, leak: dict[str, Any]) -> RawFindingDraft:
        secret_value = str(leak.get("Secret") or "")
        payload = dict(leak)
        for field in ("Secret", "Match"):
            if payload.get(field):
                payload[field] = REDACTED

        rule = str(leak.get("RuleID") or "secret")
        file_path = leak.get("File")
        start_line = leak.get("StartLine")
        hints = {"secret_hash": hash_secret(secret_value)} if secret_value else {}

        return RawFindingDraft(
            rule_id=rule[:300],
            title=str(leak.get("Description") or f"Secret detected ({rule})")[:2000],
            severity="high",
            finding_class="secret",
            file_path=str(file_path) if file_path else None,
            line=start_line if isinstance(start_line, int) else None,
            payload=payload,
            hints=hints,
        )
