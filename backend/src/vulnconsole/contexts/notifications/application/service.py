"""Notification dispatch: send a composed Message to every enabled channel and
record each attempt. If no external channel is configured, the notification is
still recorded (channel 'log') so the pipeline is always functional and auditable.
"""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from vulnconsole.contexts.notifications.application.messages import Message
from vulnconsole.contexts.notifications.domain.models import (
    STATUS_FAILED,
    STATUS_SENT,
    Notification,
)
from vulnconsole.contexts.notifications.infrastructure.providers import Notifier, build_notifiers
from vulnconsole.shared.config import get_settings

logger = structlog.get_logger(__name__)


def _record(
    session: AsyncSession,
    message: Message,
    *,
    channel: str,
    target: str,
    status: str,
    error: str | None,
) -> None:
    session.add(
        Notification(
            event=message.event,
            channel=channel,
            target=target,
            subject=message.subject,
            finding_id=uuid.UUID(message.finding_id),
            status=status,
            error=error,
        )
    )


async def dispatch(
    session: AsyncSession, message: Message, *, notifiers: list[Notifier] | None = None
) -> int:
    """Send to every enabled channel; return the count of successful sends."""
    active = [n for n in (notifiers or build_notifiers(get_settings())) if n.enabled()]

    if not active:
        # Always leave an auditable record even with no channels configured.
        _record(
            session,
            message,
            channel="log",
            target="local-log",
            status=STATUS_SENT,
            error=None,
        )
        await session.commit()
        logger.info(
            "notification.logged",
            notify_event=message.event,
            subject=message.subject,
            link=message.link,
        )
        return 0

    sent = 0
    for notifier in active:
        try:
            await notifier.send(message)
            _record(
                session,
                message,
                channel=notifier.channel,
                target=notifier.target(),
                status=STATUS_SENT,
                error=None,
            )
            sent += 1
            logger.info("notification.sent", channel=notifier.channel, notify_event=message.event)
        except Exception as exc:  # one channel failing must not block the others
            _record(
                session,
                message,
                channel=notifier.channel,
                target=notifier.target(),
                status=STATUS_FAILED,
                error=str(exc)[:2000],
            )
            logger.error(
                "notification.failed",
                channel=notifier.channel,
                notify_event=message.event,
                error=str(exc),
            )
    await session.commit()
    return sent
