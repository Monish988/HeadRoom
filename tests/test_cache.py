from unittest.mock import AsyncMock, patch

import pytest

from headroom.cache.redis_cache import RedisCache


@pytest.fixture
def cache():
    return RedisCache(redis_url="redis://localhost:6379/0")


@pytest.fixture
def mock_redis():
    with patch("headroom.cache.redis_cache.Redis.from_url", new_callable=AsyncMock) as m:
        client = AsyncMock()
        m.return_value = client
        yield client


@pytest.mark.asyncio
async def test_cache_set_and_get(cache, mock_redis):
    mock_redis.get.return_value = "hello"
    mock_redis.ping.return_value = True
    await cache.connect()
    await cache.set_cached("hello world", "hello")
    result = await cache.get_cached("hello world")
    assert result == "hello"


@pytest.mark.asyncio
async def test_cache_miss(cache, mock_redis):
    mock_redis.get.return_value = None
    mock_redis.ping.return_value = True
    await cache.connect()
    result = await cache.get_cached("nonexistent_key_xyz")
    assert result is None


@pytest.mark.asyncio
async def test_cache_stats(cache, mock_redis):
    mock_redis.info.return_value = {"used_memory_human": "1MB"}
    mock_redis.dbsize.return_value = 42
    mock_redis.ping.return_value = True
    await cache.connect()
    stats = await cache.get_stats()
    assert stats["connected"] is True
    assert stats["total_keys"] == 42


@pytest.mark.asyncio
async def test_cache_when_disconnected(cache):
    result = await cache.get_cached("anything")
    assert result is None


@pytest.mark.asyncio
async def test_set_cached_when_disconnected(cache):
    await cache.set_cached("key", "value")


@pytest.mark.asyncio
async def test_connect_graceful_degradation(cache):
    with patch("headroom.cache.redis_cache.Redis.from_url", side_effect=ConnectionError("No Redis")):
        await cache.connect()
    result = await cache.get_cached("anything")
    assert result is None
    stats = await cache.get_stats()
    assert stats["connected"] is False
