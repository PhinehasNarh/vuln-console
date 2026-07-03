"""Domain event envelope and the NATS JetStream event bus."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import nats
import structlog
from nats.aio.client import Client as NatsClient
from nats.aio.msg import Msg
from nats.js import JetStreamContext
from nats.js.api import StreamConfig
from nats.js.errors import BadRequestError
from pydantic import BaseModel, Field

from vulnconsole.shared.config import get_settings
from vulnconsole.shared.ids import uuid7

logger = structlog.get_logger(__name__)

DAY_SECONDS = 24 * 3600

# Subjects follow <context>.<entity>.<past_tense_event>
# (docs/architecture/service-decomposition.md).
SCAN_RECEIVED = "ingestion.scan.received"
SCAN_PARSED = "ingestion.scan.parsed"
SCAN_FAILED = "ingestion.scan.failed"
FINDING_CREATED = "normalization.finding.created"
FINDING_UPDATED = "normalization.finding.updated"
FINDING_ASSIGNED = "triage.finding.assigned"
SLA_BREACHED = "risk.sla.breached"

STREAMS: tuple[StreamConfig, ...] = (
    StreamConfig(name="INGESTION", subjects=["ingestion.>"], max_age=7 * DAY_SECONDS),
    StreamConfig(
        name="FINDINGS",
        subjects=["normalization.>", "enrichment.>", "risk.>"],
        max_age=30 * DAY_SECONDS,
    ),
    StreamConfig(name="WORKFLOW", subjects=["triage.>", "remediation.>"], max_age=90 * DAY_SECONDS),
    StreamConfig(name="OUTBOUND", subjects=["notifications.>", "ai.>"], max_age=7 * DAY_SECONDS),
)


class EventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid7()))
    subject: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor: str = "system"
    correlation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class EventBusNotConnectedError(RuntimeError):
    pass


class EventBus:
    def __init__(self) -> None:
        self._nc: NatsClient | None = None
        self._js: JetStreamContext | None = None

    @property
    def connected(self) -> bool:
        return self._nc is not None and self._nc.is_connected

    async def connect(self) -> None:
        self._nc = await nats.connect(get_settings().nats_url)
        self._js = self._nc.jetstream()
        for stream in STREAMS:
            try:
                await self._js.add_stream(stream)
            except BadRequestError:
                # Stream exists with a different config; converge it.
                await self._js.update_stream(stream)

    async def close(self) -> None:
        if self._nc is not None and self._nc.is_connected:
            await self._nc.drain()
        self._nc = None
        self._js = None

    def _jetstream(self) -> JetStreamContext:
        if self._js is None:
            raise EventBusNotConnectedError("event bus is not connected")
        return self._js

    async def publish(self, envelope: EventEnvelope) -> None:
        await self._jetstream().publish(
            envelope.subject, envelope.model_dump_json().encode("utf-8")
        )
        logger.info("event.published", subject=envelope.subject, event_id=envelope.event_id)

    async def subscribe(
        self,
        subject: str,
        *,
        durable: str,
        handler: Callable[[Msg], Awaitable[None]],
    ) -> None:
        await self._jetstream().subscribe(subject, durable=durable, cb=handler, manual_ack=True)
        logger.info("event.subscribed", subject=subject, durable=durable)
