import time

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class Cache:
    """Redis-backed cache with transparent in-memory fallback so the app
    runs at zero cost without any Redis server."""

    def __init__(self) -> None:
        self._redis = None
        self._mem: dict[str, tuple[str, float]] = {}
        self._redis_checked = False

    async def _get_redis(self):
        if self._redis_checked:
            return self._redis
        self._redis_checked = True
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(
                settings.redis_url, socket_connect_timeout=1, decode_responses=True
            )
            await client.ping()
            self._redis = client
            log.info("cache.redis_connected")
        except Exception:
            log.info("cache.redis_unavailable_using_memory")
            self._redis = None
        return self._redis

    async def get(self, key: str) -> str | None:
        redis = await self._get_redis()
        if redis is not None:
            try:
                return await redis.get(key)
            except Exception:
                pass
        entry = self._mem.get(key)
        if entry is None:
            return None
        value, expires = entry
        if expires < time.monotonic():
            del self._mem[key]
            return None
        return value

    async def set(self, key: str, value: str, ttl: int = 3600) -> None:
        redis = await self._get_redis()
        if redis is not None:
            try:
                await redis.set(key, value, ex=ttl)
                return
            except Exception:
                pass
        self._mem[key] = (value, time.monotonic() + ttl)


cache = Cache()
