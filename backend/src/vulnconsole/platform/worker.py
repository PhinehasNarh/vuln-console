"""Worker composition root: NATS consumers driving the finding pipeline plus
the periodic SLA breach scan."""

import asyncio
import contextlib
import json
import signal
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from nats.aio.msg import Msg
from sqlalchemy.ext.asyncio import AsyncSession

import vulnconsole.contexts.ingestion.connectors  # noqa: F401  (registers built-in connectors)
from vulnconsole.contexts.ingestion.application import service as ingestion_service
from vulnconsole.contexts.normalization.application import service as normalization_service
from vulnconsole.contexts.normalization.domain.models import Finding
from vulnconsole.contexts.notifications.application import service as notifications_service
from vulnconsole.contexts.notifications.application.messages import (
    FindingRef,
    Message,
    build_assignment,
    build_sla_breach,
)
from vulnconsole.shared.config import get_settings
from vulnconsole.shared.db import get_session_factory
from vulnconsole.shared.events import (
    FINDING_ASSIGNED,
    SCAN_PARSED,
    SCAN_RECEIVED,
    SLA_BREACHED,
    EventBus,
)
from vulnconsole.shared.logging import configure_logging

logger = structlog.get_logger(__name__)

MAX_DELIVERIES = 5
RETRY_DELAY_SECONDS = 10


async def _ack_with_retry(
    msg: Msg, name: str, work: Callable[[], Awaitable[None]], *, ref: str
) -> None:
    """Run work; ack on success, nak-with-delay on failure until MAX_DELIVERIES."""
    try:
        await work()
    except Exception as exc:
        deliveries = msg.metadata.num_delivered or 0
        if deliveries >= MAX_DELIVERIES:
            logger.error("worker.giving_up", handler=name, ref=ref, error=str(exc))
            await msg.ack()
        else:
            logger.warning(
                "worker.retrying", handler=name, ref=ref, deliveries=deliveries, error=str(exc)
            )
            await msg.nak(delay=RETRY_DELAY_SECONDS)
        return
    await msg.ack()


def _payload_id(msg: Msg, name: str, key: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(json.loads(msg.data)["payload"][key])
    except (ValueError, KeyError, TypeError) as exc:
        logger.error("worker.bad_message", handler=name, error=str(exc))
        return None


ScanHandler = Callable[[AsyncSession, EventBus, uuid.UUID], Awaitable[None]]


def make_scan_handler(
    bus: EventBus, name: str, func: ScanHandler
) -> Callable[[Msg], Awaitable[None]]:
    async def handle(msg: Msg) -> None:
        scan_id = _payload_id(msg, name, "scan_id")
        if scan_id is None:
            await msg.ack()
            return

        async def work() -> None:
            async with get_session_factory()() as session:
                await func(session, bus, scan_id)

        await _ack_with_retry(msg, name, work, ref=str(scan_id))

    return handle


MessageBuilder = Callable[[Finding, dict[str, Any]], Message]


def _finding_ref(finding: Finding) -> FindingRef:
    return FindingRef(
        id=str(finding.id),
        title=finding.title,
        severity=finding.severity,
        repository=finding.repository,
        owner=finding.owner,
    )


def make_notification_handler(
    name: str, builder: MessageBuilder
) -> Callable[[Msg], Awaitable[None]]:
    async def handle(msg: Msg) -> None:
        finding_id = _payload_id(msg, name, "finding_id")
        if finding_id is None:
            await msg.ack()
            return
        payload = json.loads(msg.data)["payload"]

        async def work() -> None:
            async with get_session_factory()() as session:
                finding = await normalization_service.get_finding(session, finding_id)
                if finding is None:
                    logger.warning("notify.finding_missing", finding_id=str(finding_id))
                    return
                await notifications_service.dispatch(session, builder(finding, payload))

        await _ack_with_retry(msg, name, work, ref=str(finding_id))

    return handle


async def sla_scan_loop(bus: EventBus, stop: asyncio.Event) -> None:
    interval = get_settings().sla_scan_interval_seconds
    while not stop.is_set():
        try:
            async with get_session_factory()() as session:
                await normalization_service.scan_sla_breaches(session, bus)
        except Exception as exc:
            logger.error("sla.scan_failed", error=str(exc))
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=interval)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    bus = EventBus()
    await bus.connect()
    await bus.subscribe(
        SCAN_RECEIVED,
        durable="worker-parse",
        handler=make_scan_handler(bus, "parse", ingestion_service.parse_scan),
    )
    await bus.subscribe(
        SCAN_PARSED,
        durable="worker-normalize",
        handler=make_scan_handler(bus, "normalize", normalization_service.normalize_scan),
    )
    await bus.subscribe(
        FINDING_ASSIGNED,
        durable="worker-notify-assigned",
        handler=make_notification_handler(
            "notify-assigned", lambda finding, _payload: build_assignment(_finding_ref(finding))
        ),
    )
    await bus.subscribe(
        SLA_BREACHED,
        durable="worker-notify-breach",
        handler=make_notification_handler(
            "notify-breach",
            lambda finding, payload: build_sla_breach(_finding_ref(finding), payload.get("due_at")),
        ),
    )
    logger.info("worker.started")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        # add_signal_handler is not implemented on the Windows event loop.
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)

    sla_task = asyncio.create_task(sla_scan_loop(bus, stop))
    await stop.wait()
    sla_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await sla_task
    await bus.close()
    logger.info("worker.stopped")


if __name__ == "__main__":
    asyncio.run(main())
