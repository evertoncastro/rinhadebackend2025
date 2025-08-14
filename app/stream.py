import os
import orjson
from typing import Any, Dict, Optional
from redis.asyncio import Redis
from redis.exceptions import ResponseError


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
PAYMENTS_STREAM = os.getenv("PAYMENTS_STREAM", "payments-stream")
PAYMENTS_CONSUMER_GROUP = os.getenv("PAYMENTS_CONSUMER_GROUP", "payments-workers")
PAYMENTS_STREAM_MAXLEN = int(os.getenv("PAYMENTS_STREAM_MAXLEN", "0"))
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
REDIS_HEALTH_CHECK_INTERVAL = int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30"))

_redis_client: Optional[Redis] = None
_redis_write_client: Optional[Redis] = None


async def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            REDIS_URL, 
            decode_responses=False, 
            max_connections=REDIS_MAX_CONNECTIONS,
            health_check_interval=REDIS_HEALTH_CHECK_INTERVAL,
            socket_keepalive=True,
            socket_keepalive_options={},
            retry_on_timeout=True
        )
    assert _redis_client is not None
    return _redis_client


async def get_redis_write() -> Redis:
    """Optimized Redis client specifically for write operations"""
    global _redis_write_client
    if _redis_write_client is None:
        _redis_write_client = Redis.from_url(
            REDIS_URL,
            decode_responses=False,
            max_connections=REDIS_MAX_CONNECTIONS // 2,  # Dedicated pool for writes
            health_check_interval=60,  # Less frequent health checks
            socket_keepalive=True,
            socket_keepalive_options={},
            retry_on_timeout=False  # Fail fast for writes
        )
    assert _redis_write_client is not None
    return _redis_write_client


async def close_redis() -> None:
    global _redis_client, _redis_write_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
    if _redis_write_client is not None:
        await _redis_write_client.close()
        _redis_write_client = None


async def ensure_stream_exists(group_name: Optional[str] = PAYMENTS_CONSUMER_GROUP) -> None:
    redis = await get_redis()
    if group_name:
        try:
            await redis.xgroup_create(name=PAYMENTS_STREAM, groupname=group_name, id="$", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
    else:
        await redis.xadd(PAYMENTS_STREAM, {"init": "1"})


async def append_payment_to_stream(payload: Dict[str, Any]) -> None:
    redis = await get_redis_write()
    serialized_data = orjson.dumps(payload)
    await redis.xadd(PAYMENTS_STREAM, {b"data": serialized_data})
