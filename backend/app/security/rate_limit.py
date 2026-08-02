import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from redis.asyncio import Redis

from app.core.config import Settings


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after: int


class RateLimiter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._redis: Redis | None = None
        self._local: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()

    async def check(self, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        if self.settings.environment == "test":
            limit = max(limit, 10_000)
        try:
            return await self._redis_check(key, limit, window_seconds)
        except Exception:
            if self.settings.environment == "production":
                return RateLimitDecision(False, 0, 5)
            return await self._local_check(key, limit, window_seconds)

    async def _redis_check(self, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        if self._redis is None:
            self._redis = Redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=0.2,
                socket_timeout=0.2,
            )
        bucket = f"cybermentor:rate:{key}:{int(time.time()) // window_seconds}"
        count = int(await self._redis.incr(bucket))
        if count == 1:
            await self._redis.expire(bucket, window_seconds + 1)
        retry = window_seconds - (int(time.time()) % window_seconds)
        return RateLimitDecision(count <= limit, max(0, limit - count), retry)

    async def _local_check(self, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        now = time.monotonic()
        async with self._lock:
            events = self._local[key]
            while events and events[0] <= now - window_seconds:
                events.popleft()
            if len(events) >= limit:
                retry = max(1, int(window_seconds - (now - events[0])))
                return RateLimitDecision(False, 0, retry)
            events.append(now)
            return RateLimitDecision(True, max(0, limit - len(events)), 0)


def policy_for(method: str, path: str) -> tuple[int, int] | None:
    if method in {"GET", "HEAD", "OPTIONS"}:
        return None
    if path.endswith("/auth/login"):
        return (10, 60)
    if path.endswith("/auth/register") or path.endswith("/auth/forgot-password"):
        return (5, 60)
    if "/mentor/" in path:
        return (30, 60)
    return (180, 60)
