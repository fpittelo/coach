"""Unit tests for the TTLCache implementation."""

import asyncio

import pytest

from coach_mcp.cache import TTLCache


@pytest.mark.asyncio
async def test_cache_get_returns_none_for_missing_key():
    """A fresh cache should return None for an unknown key."""
    cache = TTLCache(default_ttl=300)

    result = await cache.get("missing")

    assert result is None


@pytest.mark.asyncio
async def test_cache_set_and_get():
    """Setting a value should make it retrievable."""
    cache = TTLCache(default_ttl=300)

    await cache.set("key", "value")
    result = await cache.get("key")

    assert result == "value"


@pytest.mark.asyncio
async def test_cache_expiration_uses_default_ttl():
    """Values should expire after the default TTL elapses."""
    cache = TTLCache(default_ttl=0)

    await cache.set("key", "value")
    await asyncio.sleep(0.01)
    result = await cache.get("key")

    assert result is None


@pytest.mark.asyncio
async def test_cache_expiration_uses_explicit_ttl():
    """Values should expire after an explicitly provided TTL."""
    cache = TTLCache(default_ttl=300)

    await cache.set("key", "value", ttl=0)
    await asyncio.sleep(0.01)
    result = await cache.get("key")

    assert result is None


@pytest.mark.asyncio
async def test_cache_non_expiring_value_with_negative_ttl():
    """A negative TTL should keep a value alive indefinitely."""
    cache = TTLCache(default_ttl=300)

    await cache.set("key", "value", ttl=-1)
    result = await cache.get("key")

    assert result == "value"


@pytest.mark.asyncio
async def test_cache_clear_removes_all_values():
    """Clearing the cache should remove every stored value."""
    cache = TTLCache(default_ttl=300)

    await cache.set("a", 1)
    await cache.set("b", 2)
    await cache.clear()

    assert await cache.get("a") is None
    assert await cache.get("b") is None


@pytest.mark.asyncio
async def test_cache_invalidate_removes_single_key():
    """Invalidating a key should remove only that key."""
    cache = TTLCache(default_ttl=300)

    await cache.set("a", 1)
    await cache.set("b", 2)
    await cache.invalidate("a")

    assert await cache.get("a") is None
    assert await cache.get("b") == 2


@pytest.mark.asyncio
async def test_cache_invalidate_missing_key_is_safe():
    """Invalidating a non-existent key should not raise an error."""
    cache = TTLCache(default_ttl=300)

    await cache.invalidate("missing")

    assert await cache.get("missing") is None


@pytest.mark.asyncio
async def test_cache_invalidate_prefix_removes_matching_keys():
    """Invalidating a prefix should remove all matching keys and leave others."""
    cache = TTLCache(default_ttl=300)

    await cache.set("events:0:2026-08-01:2026-08-22:WORKOUT", [])
    await cache.set("events:0:2026-08-01:2026-08-22:NOTE", [])
    await cache.set("profile:0", {})
    await cache.invalidate_prefix("events:0:")

    assert await cache.get("events:0:2026-08-01:2026-08-22:WORKOUT") is None
    assert await cache.get("events:0:2026-08-01:2026-08-22:NOTE") is None
    assert await cache.get("profile:0") == {}


@pytest.mark.asyncio
async def test_cache_invalidate_prefix_missing_prefix_is_safe():
    """Invalidating a prefix with no matches should not raise an error."""
    cache = TTLCache(default_ttl=300)

    await cache.set("profile:0", {})
    await cache.invalidate_prefix("wellness:0:")

    assert await cache.get("profile:0") == {}


@pytest.mark.asyncio
async def test_cache_concurrent_set_and_get():
    """Concurrent set/get operations should be safe under the async lock."""
    cache = TTLCache(default_ttl=300)

    async def writer(value: int) -> None:
        await cache.set(f"key_{value}", value)

    async def reader(value: int) -> int | None:
        return await cache.get(f"key_{value}")

    writers = [asyncio.create_task(writer(i)) for i in range(50)]
    await asyncio.gather(*writers)

    readers = [asyncio.create_task(reader(i)) for i in range(50)]
    results = await asyncio.gather(*readers)

    assert results == list(range(50))


@pytest.mark.asyncio
async def test_cache_concurrent_same_key_writes():
    """Many concurrent writes to the same key should leave a valid value."""
    cache = TTLCache(default_ttl=300)

    async def writer(value: int) -> None:
        await cache.set("shared", value)

    await asyncio.gather(*[asyncio.create_task(writer(i)) for i in range(100)])

    result = await cache.get("shared")
    assert isinstance(result, int)
