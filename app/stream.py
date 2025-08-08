import os
import json
from typing import Any, Dict, Optional
from redis.asyncio import Redis
from redis.exceptions import ResponseError


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
PAYMENTS_STREAM = os.getenv("PAYMENTS_STREAM", "payments-stream")
PAYMENTS_CONSUMER_GROUP = os.getenv("PAYMENTS_CONSUMER_GROUP", "payments-workers")

_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
    assert _redis_client is not None
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


async def ensure_stream_exists(group_name: Optional[str] = PAYMENTS_CONSUMER_GROUP) -> None:
    redis = await get_redis()
    # Ensure stream exists and optionally ensure a consumer group exists
    if group_name:
        try:
            # Create group at end ($), create stream if missing
            await redis.xgroup_create(name=PAYMENTS_STREAM, groupname=group_name, id="$", mkstream=True)
        except ResponseError as exc:
            # BUSYGROUP means group already exists; ignore
            if "BUSYGROUP" not in str(exc):
                raise
    else:
        # If no group management, at least ensure the stream exists using XADD with a dummy field removed immediately
        await redis.xadd(PAYMENTS_STREAM, {"init": "1"})


async def append_payment_to_stream(payload: Dict[str, Any]) -> str:
    redis = await get_redis()
    message_id = await redis.xadd(PAYMENTS_STREAM, {"data": json.dumps(payload)})
    return str(message_id)


