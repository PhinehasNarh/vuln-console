import json
from typing import Any

import httpx
import pytest

from vulnconsole.contexts.notifications.application import service as dispatch_service
from vulnconsole.contexts.notifications.application.messages import (
    FindingRef,
    Message,
    build_assignment,
    build_sla_breach,
)
from vulnconsole.contexts.notifications.infrastructure import providers
from vulnconsole.contexts.notifications.infrastructure.providers import (
    EmailNotifier,
    SlackNotifier,
    TeamsNotifier,
    build_notifiers,
)
from vulnconsole.shared.config import Settings

REF = FindingRef(
    id="0197fc00-0000-7000-8000-000000000000",
    title="S3 bucket is public",
    severity="critical",
    repository="acme/app",
    owner="sana",
)
SLACK_URL = "https://hooks.slack.example/T/B/X"


# ---- message composition ----


def test_assignment_message_mentions_owner_and_link() -> None:
    msg = build_assignment(REF)
    assert msg.event == "finding.assigned"
    assert "sana" in msg.subject
    assert "acme/app" in msg.body
    assert msg.finding_id == REF.id
    assert msg.link.endswith(f"/findings/{REF.id}")


def test_breach_message_reports_due_and_owner() -> None:
    msg = build_sla_breach(REF, "2026-07-04T12:00:00+00:00")
    assert msg.event == "sla.breached"
    assert "SLA breached" in msg.subject
    assert "sana" in msg.body
    assert "2026-07-04" in msg.body


# ---- provider enablement ----


def test_provider_enablement_depends_on_settings() -> None:
    empty = Settings(_env_file=None)  # type: ignore[call-arg]
    assert not SlackNotifier(empty).enabled()
    assert not TeamsNotifier(empty).enabled()
    assert not EmailNotifier(empty).enabled()

    configured = Settings(  # type: ignore[call-arg]
        _env_file=None,
        slack_webhook_url=SLACK_URL,
        teams_webhook_url="https://outlook.office.example/webhook/abc",
        smtp_host="smtp.example.com",
        notify_email_to="secops@example.com",
    )
    enabled = {n.channel for n in build_notifiers(configured) if n.enabled()}
    assert enabled == {"slack", "teams", "email"}


# ---- real send() through a mock transport ----


def _use_transport(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    real_client = httpx.AsyncClient

    def fake_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs.pop("transport", None)
        return real_client(*args, transport=transport, **kwargs)

    monkeypatch.setattr(providers.httpx, "AsyncClient", fake_client)


async def test_slack_send_posts_expected_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200)

    _use_transport(monkeypatch, httpx.MockTransport(handler))
    await SlackNotifier(Settings(_env_file=None, slack_webhook_url=SLACK_URL)).send(  # type: ignore[call-arg]
        build_assignment(REF)
    )
    assert captured["url"] == SLACK_URL
    assert "S3 bucket is public" in captured["payload"]["text"]


async def test_teams_send_uses_messagecard(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200)

    _use_transport(monkeypatch, httpx.MockTransport(handler))
    settings = Settings(_env_file=None, teams_webhook_url="https://outlook.office.example/webhook")  # type: ignore[call-arg]
    await TeamsNotifier(settings).send(build_sla_breach(REF, None))
    assert captured["payload"]["@type"] == "MessageCard"
    assert captured["payload"]["potentialAction"][0]["targets"][0]["uri"].endswith(REF.id)


async def test_slack_send_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_transport(monkeypatch, httpx.MockTransport(lambda _req: httpx.Response(500)))
    with pytest.raises(httpx.HTTPStatusError):
        await SlackNotifier(Settings(_env_file=None, slack_webhook_url=SLACK_URL)).send(  # type: ignore[call-arg]
            build_assignment(REF)
        )


# ---- dispatch fan-out and recording (fake session, no DB) ----


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.commits = 0

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1


class FakeNotifier:
    def __init__(self, channel: str, *, fail: bool = False) -> None:
        self.channel = channel
        self._fail = fail
        self.calls = 0

    def enabled(self) -> bool:
        return True

    def target(self) -> str:
        return f"{self.channel}-target"

    async def send(self, message: Message) -> None:
        self.calls += 1
        if self._fail:
            raise RuntimeError("boom")


async def test_dispatch_records_log_when_no_channels() -> None:
    session = FakeSession()
    sent = await dispatch_service.dispatch(session, build_assignment(REF), notifiers=[])  # type: ignore[arg-type]
    assert sent == 0
    assert len(session.added) == 1
    assert session.added[0].channel == "log"
    assert session.added[0].status == "sent"


async def test_dispatch_fans_out_and_records_each_outcome() -> None:
    session = FakeSession()
    ok = FakeNotifier("slack")
    bad = FakeNotifier("teams", fail=True)
    sent = await dispatch_service.dispatch(
        session, build_assignment(REF), notifiers=[ok, bad]  # type: ignore[list-item]
    )
    assert sent == 1
    assert ok.calls == 1 and bad.calls == 1
    outcomes = {n.channel: n.status for n in session.added}
    assert outcomes == {"slack": "sent", "teams": "failed"}
    assert next(n for n in session.added if n.channel == "teams").error
