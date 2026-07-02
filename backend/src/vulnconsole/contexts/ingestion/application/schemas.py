"""Ingestion request/response models."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository: str
    branch: str | None
    commit_sha: str | None
    format: str
    tool_name: str | None
    status: str
    error: str | None
    artifact_size: int
    created_at: datetime
    updated_at: datetime
