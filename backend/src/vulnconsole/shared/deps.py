"""FastAPI dependencies for app-scoped infrastructure clients."""

from fastapi import Request
from redis.asyncio import Redis

from vulnconsole.shared.events import EventBus


def get_event_bus(request: Request) -> EventBus:
    return request.app.state.bus  # type: ignore[no-any-return]


def get_redis(request: Request) -> Redis:
    return request.app.state.redis  # type: ignore[no-any-return]
