"""Worker composition root: NATS consumers driving the finding pipeline."""

import asyncio
import contextlib
import json
import signal
import uuid
from collections.abc import Awaitable, Callable

import structlog
from nats.aio.msg import Msg
from sqlalchemy.ext.asyncio import AsyncSession

import vulnconsole.contexts.ingestion.connectors  # noqa: F401  (registers built-in connectors)
from vulnconsole.contexts.ingestion.application import service as ingestion_service
from vulnconsole.contexts.normalization.application import service as normalization_service
from vulnconsole.shared.config import get_settings
from vulnconsole.shared.db import get_session_factory
from vulnconsole.shared.events import SCAN_PARSED, SCAN_RECEIVED, EventBus
from vulnconsole.shared.logging import configure_logging

logger = structlog.get_logger(__name__)

MAX_DELIVERIES = 5
RETRY_DELAY_SECONDS = 10

ScanHandler = Callable[[AsyncSession, EventBus, uuid.UUID], Awaitable[None]]


def make_handler(bus: EventBus, name: str, func: ScanHandler) -> Callable[[Msg], Awaitable[None]]:
    async def handle(msg: Msg) -> None:
        try:
            envelope = json.loads(msg.data)
            scan_id = uuid.UUID(envelope["payload"]["scan_id"])
        except (ValueError, KeyError, TypeError) as exc:
            # Malformed message: never processable, do not redeliver.
            logger.error("worker.bad_message", handler=name, error=str(exc))
            await msg.ack()
            return

        try:
            async with get_session_factory()() as session:
                await func(session, bus, scan_id)
        except Exception as exc:
            deliveries = msg.metadata.num_delivered or 0
            if deliveries >= MAX_DELIVERIES:
                logger.error(
                    "worker.giving_up",
                    handler=name,
                    scan_id=str(scan_id),
                    deliveries=deliveries,
                    error=str(exc),
                )
                await msg.ack()
            else:
                logger.warning(
                    "worker.retrying",
                    handler=name,
                    scan_id=str(scan_id),
                    deliveries=deliveries,
                    error=str(exc),
                )
                await msg.nak(delay=RETRY_DELAY_SECONDS)
            return

        await msg.ack()

    return handle


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    bus = EventBus()
    await bus.connect()
    await bus.subscribe(
        SCAN_RECEIVED,
        durable="worker-parse",
        handler=make_handler(bus, "parse", ingestion_service.parse_scan),
    )
    await bus.subscribe(
        SCAN_PARSED,
        durable="worker-normalize",
        handler=make_handler(bus, "normalize", normalization_service.normalize_scan),
    )
    logger.info("worker.started")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        # add_signal_handler is not implemented on the Windows event loop.
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)
    await stop.wait()
    await bus.close()
    logger.info("worker.stopped")


if __name__ == "__main__":
    asyncio.run(main())
