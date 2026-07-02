"""Fixed-window rate limiting backed by Redis."""

from redis.asyncio import Redis


async def within_rate_limit(redis: Redis, key: str, *, limit: int, window_seconds: int) -> bool:
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, window_seconds)
    return int(current) <= limit
