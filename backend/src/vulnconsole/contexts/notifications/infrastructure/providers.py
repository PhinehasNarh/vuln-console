"""Notification channel providers: Slack, Microsoft Teams, and email.

Each provider is enabled only when its settings are present. Sending raises on
failure so the dispatcher can record the outcome per channel.
"""

import smtplib
from email.message import EmailMessage
from typing import Protocol, runtime_checkable

import anyio.to_thread
import httpx

from vulnconsole.contexts.notifications.application.messages import Message
from vulnconsole.shared.config import Settings

HTTP_TIMEOUT = 10.0


@runtime_checkable
class Notifier(Protocol):
    channel: str

    def enabled(self) -> bool: ...

    def target(self) -> str: ...

    async def send(self, message: Message) -> None: ...


class SlackNotifier:
    channel = "slack"

    def __init__(self, settings: Settings) -> None:
        self._url = settings.slack_webhook_url

    def enabled(self) -> bool:
        return bool(self._url)

    def target(self) -> str:
        return "slack-webhook"

    async def send(self, message: Message) -> None:
        payload = {"text": f"*{message.subject}*\n{message.body}\n{message.link}"}
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(self._url, json=payload)
            response.raise_for_status()


class TeamsNotifier:
    channel = "teams"

    def __init__(self, settings: Settings) -> None:
        self._url = settings.teams_webhook_url

    def enabled(self) -> bool:
        return bool(self._url)

    def target(self) -> str:
        return "teams-webhook"

    async def send(self, message: Message) -> None:
        # MessageCard is the widely supported Teams incoming-webhook format.
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": message.subject,
            "themeColor": "D7263D",
            "title": message.subject,
            "text": message.body.replace("\n", "\n\n"),
            "potentialAction": [
                {
                    "@type": "OpenUri",
                    "name": "Open finding",
                    "targets": [{"os": "default", "uri": message.link}],
                }
            ],
        }
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(self._url, json=payload)
            response.raise_for_status()


class EmailNotifier:
    channel = "email"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def enabled(self) -> bool:
        s = self._settings
        return bool(s.smtp_host and s.notify_email_to)

    def target(self) -> str:
        return self._settings.notify_email_to

    def _send_sync(self, message: Message) -> None:
        s = self._settings
        email = EmailMessage()
        email["Subject"] = message.subject
        email["From"] = s.smtp_from
        email["To"] = s.notify_email_to
        email.set_content(f"{message.body}\n\n{message.link}")
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=HTTP_TIMEOUT) as server:
            if s.smtp_use_tls:
                server.starttls()
            if s.smtp_username:
                server.login(s.smtp_username, s.smtp_password)
            server.send_message(email)

    async def send(self, message: Message) -> None:
        await anyio.to_thread.run_sync(self._send_sync, message)


def build_notifiers(settings: Settings) -> list[Notifier]:
    return [SlackNotifier(settings), TeamsNotifier(settings), EmailNotifier(settings)]
