"""Prowler connector for cloud security posture findings (AWS, Azure, GCP).

Handles both Prowler output shapes:
- v4+ OCSF JSON (the current default): a list of OCSF Detection Findings keyed
  by metadata.event_code, finding_info.title, cloud.provider, resources[].uid.
- v3 native JSON: a list keyed by CheckID, Status, AccountId, ResourceArn.

Only failing checks are ingested; PASS results are not findings. Every finding
normalizes to the shared 'cloud' class so AWS and Azure land in one view and
the same failing control on the same resource correlates across re-scans
(fingerprint v2, ADR-0007).
"""

import json
from typing import Any

from vulnconsole.contexts.ingestion.connectors.base import (
    ConnectorError,
    ParseResult,
    RawFindingDraft,
    normalize_severity_name,
)


class ProwlerConnector:
    format_id = "prowler-json"
    display_name = "Prowler (cloud, OCSF or native JSON)"

    def sniff(self, artifact: bytes) -> bool:
        head = artifact[:8192].decode("utf-8", errors="replace")
        if not head.lstrip().startswith("["):
            return False
        is_ocsf = '"finding_info"' in head and ('"event_code"' in head or '"cloud"' in head)
        is_native = '"CheckID"' in head and '"Status"' in head
        return is_ocsf or is_native

    def parse(self, artifact: bytes) -> ParseResult:
        try:
            document = json.loads(artifact)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ConnectorError(f"artifact is not valid JSON: {exc}") from exc
        if not isinstance(document, list):
            raise ConnectorError("artifact is not a Prowler report: expected a JSON array")

        findings: list[RawFindingDraft] = []
        parsed_any = False
        for item in document:
            if not isinstance(item, dict):
                continue
            if "finding_info" in item or "metadata" in item:
                parsed_any = True
                draft = self._ocsf(item)
            elif "CheckID" in item:
                parsed_any = True
                draft = self._native(item)
            else:
                continue
            if draft is not None:
                findings.append(draft)
        if not parsed_any:
            raise ConnectorError("artifact contains no Prowler findings")
        return ParseResult(tool_name="Prowler", findings=findings)

    def _ocsf(self, item: dict[str, Any]) -> RawFindingDraft | None:
        if str(item.get("status_code") or "").upper() != "FAIL":
            return None
        metadata = item.get("metadata") or {}
        finding_info = item.get("finding_info") or {}
        cloud = item.get("cloud") or {}
        account = cloud.get("account") or {}
        resources = item.get("resources") or []
        resource = resources[0] if resources and isinstance(resources[0], dict) else {}

        check_id = str(metadata.get("event_code") or finding_info.get("uid") or "unknown")
        resource_uid = resource.get("uid") or resource.get("name")
        title = (
            finding_info.get("title")
            or item.get("status_detail")
            or check_id
        )
        return self._draft(
            check_id=check_id,
            title=str(title),
            severity=str(item.get("severity") or "medium"),
            provider=str(cloud.get("provider") or "cloud"),
            account=account.get("uid"),
            region=cloud.get("region") or resource.get("region"),
            resource_uid=resource_uid,
            resource_type=resource.get("type"),
            payload=item,
        )

    def _native(self, item: dict[str, Any]) -> RawFindingDraft | None:
        if str(item.get("Status") or "").upper() != "FAIL":
            return None
        check_id = str(item.get("CheckID") or "unknown")
        resource_uid = item.get("ResourceArn") or item.get("ResourceId")
        return self._draft(
            check_id=check_id,
            title=str(item.get("CheckTitle") or item.get("StatusExtended") or check_id),
            severity=str(item.get("Severity") or "medium"),
            provider=str(item.get("Provider") or "aws"),
            account=item.get("AccountId"),
            region=item.get("Region"),
            resource_uid=resource_uid,
            resource_type=item.get("ResourceType"),
            payload=item,
        )

    def _draft(
        self,
        *,
        check_id: str,
        title: str,
        severity: str,
        provider: str,
        account: object,
        region: object,
        resource_uid: object,
        resource_type: object,
        payload: dict[str, Any],
    ) -> RawFindingDraft:
        hints: dict[str, str] = {"provider": provider}
        if resource_uid:
            hints["resource_uid"] = str(resource_uid)
        if account:
            hints["account"] = str(account)
        if region:
            hints["region"] = str(region)
        if resource_type:
            hints["resource_type"] = str(resource_type)
        return RawFindingDraft(
            rule_id=check_id[:300],
            title=title[:2000],
            severity=normalize_severity_name(severity, default="medium"),
            finding_class="cloud",
            # The resource is the "location" of a cloud finding; shown in the table.
            file_path=str(resource_uid) if resource_uid else None,
            line=None,
            payload=payload,
            hints=hints,
        )
