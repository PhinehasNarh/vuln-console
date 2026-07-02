"""TruffleHog JSONL connector. Verified secrets are critical; values are hashed
for correlation and redacted before persistence."""

import json
from typing import Any

from vulnconsole.contexts.ingestion.connectors.base import (
    REDACTED,
    ConnectorError,
    ParseResult,
    RawFindingDraft,
    hash_secret,
)


class TruffleHogConnector:
    format_id = "trufflehog-jsonl"
    display_name = "TruffleHog (JSONL)"

    def sniff(self, artifact: bytes) -> bool:
        first_line = artifact[:4096].decode("utf-8", errors="replace").lstrip().splitlines()
        return bool(first_line) and '"DetectorName"' in first_line[0]

    def parse(self, artifact: bytes) -> ParseResult:
        try:
            text = artifact.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ConnectorError(f"artifact is not UTF-8 text: {exc}") from exc

        findings: list[RawFindingDraft] = []
        parsed_any = False
        for line_number, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ConnectorError(f"line {line_number} is not valid JSON: {exc}") from exc
            if not isinstance(record, dict) or "DetectorName" not in record:
                continue
            parsed_any = True
            findings.append(self._record(record))
        if not parsed_any:
            raise ConnectorError("artifact contains no TruffleHog records")
        return ParseResult(tool_name="TruffleHog", findings=findings)

    def _record(self, record: dict[str, Any]) -> RawFindingDraft:
        secret_value = str(record.get("Raw") or "")
        payload = dict(record)
        for field in ("Raw", "RawV2"):
            if payload.get(field):
                payload[field] = REDACTED

        detector = str(record.get("DetectorName") or "secret")
        verified = bool(record.get("Verified"))

        file_path: str | None = None
        line: int | None = None
        data = ((record.get("SourceMetadata") or {}).get("Data")) or {}
        for source in data.values():
            if isinstance(source, dict):
                file_path = source.get("file") or source.get("File") or file_path
                candidate = source.get("line") or source.get("Line")
                if isinstance(candidate, int):
                    line = candidate

        hints = {"secret_hash": hash_secret(secret_value)} if secret_value else {}
        status = "verified" if verified else "unverified"

        return RawFindingDraft(
            rule_id=f"trufflehog-{detector.lower()}"[:300],
            title=f"{detector} credential detected ({status})"[:2000],
            severity="critical" if verified else "high",
            finding_class="secret",
            file_path=str(file_path) if file_path else None,
            line=line,
            payload=payload,
            hints=hints,
        )
