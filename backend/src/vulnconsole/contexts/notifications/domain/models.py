"""Notification records: an append-only log of every dispatch attempt."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from vulnconsole.shared.db import Base
from vulnconsole.shared.ids import uuid7

SCHEMA = "notifications"

STATUS_SENT = "sent"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    event: Mapped[str] = mapped_column(String(80), index=True)
    channel: Mapped[str] = mapped_column(String(20), index=True)
    target: Mapped[str] = mapped_column(String(300))
    subject: Mapped[str] = mapped_column(Text)
    finding_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    status: Mapped[str] = mapped_column(String(12))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
