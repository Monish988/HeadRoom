import hashlib
from typing import Any, Optional

from redis.asyncio import Redis

from headroom.config import settings


class RedisCache:
    def __init__(self, redis_url: Optional[str] = None) -> None:
        self._client: Optional[Redis] = None
        self._redis_url = redis_url or settings.redis_url

    async def connect(self) -> None:
        if self._client is None:
            try:
                self._client = await Redis.from_url(
                    self._redis_url, decode_responses=True
                )
                await self._client.ping()
            except Exception:
                self._client = None

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    @staticmethod
    def _hash_key(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    async def get_cached(self, text: str) -> Optional[str]:
        if self._client is None:
            return None
        key = self._hash_key(text)
        return await self._client.get(key)

    async def set_cached(self, text: str, compressed: str, ttl: int = 3600) -> None:
        if self._client is None:
            return
        key = self._hash_key(text)
        await self._client.set(key, compressed, ex=ttl)

    async def get_stats(self) -> dict[str, Any]:
        if self._client is None:
            return {"connected": False}
        info = await self._client.info()
        return {
            "connected": True,
            "used_memory_human": info.get("used_memory_human", "N/A"),
            "total_keys": await self._client.dbsize(),
        }
