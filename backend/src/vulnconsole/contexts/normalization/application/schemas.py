"""Normalization response models."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
    tool_names: list[str]
    first_seen: datetime
    last_seen: datetime


class FindingSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scan_id: uuid.UUID
    raw_finding_id: uuid.UUID
    created_at: datetime


class FindingDetailOut(FindingOut):
    sources: list[FindingSourceOut]
