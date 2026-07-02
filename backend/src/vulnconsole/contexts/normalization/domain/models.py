"""Normalization tables: canonical findings and their raw-finding sources."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from vulnconsole.shared.db import Base
from vulnconsole.shared.ids import uuid7

SCHEMA = "normalization"

STATUS_NEW = "new"
FINDING_STATUSES = (
    "new",
    "triaged",
    "in_remediation",
    "fixed",
    "risk_accepted",
    "false_positive",
    "suppressed",
    "reopened",
)


class Finding(Base):
    """Canonical, deduplicated finding. Identity is the fingerprint."""

    __tablename__ = "findings"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    finding_class: Mapped[str] = mapped_column(String(20), index=True)
    rule_key: Mapped[str] = mapped_column(String(400))
    title: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(10), index=True)
    status: Mapped[str] = mapped_column(String(20), default=STATUS_NEW, index=True)
    repository: Mapped[str] = mapped_column(String(300), index=True)
    file_path: Mapped[str | None] = mapped_column(Text)
    line: Mapped[int | None] = mapped_column(Integer)
    package: Mapped[str | None] = mapped_column(String(300))
    cve_id: Mapped[str | None] = mapped_column(String(40), index=True)
    fixed_version: Mapped[str | None] = mapped_column(String(100))
    tool_names: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FindingSource(Base):
    """Links a canonical finding to every raw finding that fed it."""

    __tablename__ = "finding_sources"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    finding_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.findings.id"), index=True
    )
    raw_finding_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True)
    scan_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
