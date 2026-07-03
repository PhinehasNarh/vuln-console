"""Normalization request and response models."""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from vulnconsole.contexts.normalization.domain.sla import sla_status


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fingerprint: str
    finding_class: str
    rule_key: str
    title: str
    severity: str
    status: str
    repository: str
    file_path: str | None
    line: int | None
    package: str | None
    cve_id: str | None
    fixed_version: str | None
    tool_names: list[str]
    owner: str | None
    assigned_at: datetime | None
    sla_due_at: datetime | None
    sla_status: str = "none"
    first_seen: datetime
    last_seen: datetime

    @classmethod
    def from_finding(cls, finding: object) -> "FindingOut":
        out = cls.model_validate(finding)
        out.sla_status = sla_status(out.sla_due_at, out.status, datetime.now(UTC))
        return out


class AssignRequest(BaseModel):
    # owner=None clears the assignment.
    owner: str | None = Field(default=None, max_length=120)


class FindingSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scan_id: uuid.UUID
    raw_finding_id: uuid.UUID
    created_at: datetime


class FindingDetailOut(FindingOut):
    sources: list[FindingSourceOut]
