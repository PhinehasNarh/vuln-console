"""Ingestion tables: scans and raw (scanner-native) findings."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from vulnconsole.shared.db import Base
from vulnconsole.shared.ids import uuid7

SCHEMA = "ingestion"

SCAN_STATUS_RECEIVED = "received"
SCAN_STATUS_PARSED = "parsed"
SCAN_STATUS_NORMALIZED = "normalized"
SCAN_STATUS_FAILED = "failed"


class Scan(Base):
    __tablename__ = "scans"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    repository: Mapped[str] = mapped_column(String(300), index=True)
    branch: Mapped[str | None] = mapped_column(String(200))
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    format: Mapped[str] = mapped_column(String(50))
    tool_name: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default=SCAN_STATUS_RECEIVED, index=True)
    error: Mapped[str | None] = mapped_column(Text)
    artifact_key: Mapped[str] = mapped_column(String(500))
    artifact_size: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RawFinding(Base):
    """Scanner output preserved verbatim (ADR-0007). Never mutated after insert."""

    __tablename__ = "raw_findings"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    scan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.scans.id"), index=True)
    finding_class: Mapped[str] = mapped_column(String(20))
    rule_id: Mapped[str] = mapped_column(String(300))
    severity: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(Text)
    line: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
