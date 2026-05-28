import hashlib
import json
import logging
import time
from typing import Any, Optional

from config import CACHE_ENABLED, LIST_CACHE_TTL, REDIS_URL, TASK_CACHE_TTL

logger = logging.getLogger("task_api.cache")

try:
    from redis import asyncio as aioredis
    from redis.exceptions import RedisError
    _redis_lib_available = True
except ImportError:
    aioredis = None
    RedisError = Exception
    _redis_lib_available = False

_redis_client: Optional[Any] = None
_last_failure_at: float = 0.0
_RETRY_INTERVAL_SECONDS: float = 30.0


async def _get_client() -> Optional[Any]:
    global _redis_client, _last_failure_at

    if not CACHE_ENABLED or not _redis_lib_available:
        return None

    if _redis_client is not None:
        return _redis_client

    now = time.monotonic()
    if now - _last_failure_at < _RETRY_INTERVAL_SECONDS:
        return None

    try:
        client = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        await client.ping()
        _redis_client = client
        return _redis_client
    except (RedisError, OSError, Exception) as exc:
        logger.warning("Redis unavailable, falling back to direct reads: %s", exc)
        _last_failure_at = now
        _redis_client = None
        return None


async def get(key: str) -> Optional[str]:
    client = await _get_client()
    if client is None:
        return None
    try:
        return await client.get(key)
    except Exception as exc:
        logger.warning("Cache GET failed for %s: %s", key, exc)
        return None


async def setex(key: str, ttl: int, value: str) -> None:
    client = await _get_client()
    if client is None:
        return
    try:
        await client.set(key, value, ex=ttl)
    except Exception as exc:
        logger.warning("Cache SET failed for %s: %s", key, exc)


async def delete(*keys: str) -> None:
    client = await _get_client()
    if client is None or not keys:
        return
    try:
        await client.delete(*keys)
    except Exception as exc:
        logger.warning("Cache DEL failed for %s: %s", keys, exc)


async def get_list_version(user_id: int) -> int:
    client = await _get_client()
    if client is None:
        return 0
    try:
        raw = await client.get(_list_version_key(user_id))
        return int(raw) if raw is not None else 0
    except Exception as exc:
        logger.warning("Cache version read failed for user %s: %s", user_id, exc)
        return 0


async def bump_list_version(user_id: int) -> None:
    client = await _get_client()
    if client is None:
        return
    try:
        await client.incr(_list_version_key(user_id))
    except Exception as exc:
        logger.warning("Cache version bump failed for user %s: %s", user_id, exc)


def _list_version_key(user_id: int) -> str:
    return f"tasks_list_version:{user_id}"


def task_key(user_id: int, task_id: int) -> str:
    return f"task:{user_id}:{task_id}"


def list_key(user_id: int, version: int, params: dict) -> str:
    blob = json.dumps(params, sort_keys=True, default=str).encode("utf-8")
    digest = hashlib.sha256(blob).hexdigest()[:16]
    return f"tasks_list:{user_id}:v{version}:{digest}"


__all__ = [
    "CACHE_ENABLED",
    "TASK_CACHE_TTL",
    "LIST_CACHE_TTL",
    "get",
    "setex",
    "delete",
    "get_list_version",
    "bump_list_version",
    "task_key",
    "list_key",
]
