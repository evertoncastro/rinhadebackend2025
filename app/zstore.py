from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

import orjson

from .stream import get_redis


ZSET_KEY = "payments:processed"


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def add_processed(processor: str, amount: Any, processed_at: datetime, correlation_id: str | None = None) -> None:
    dt = _utc(processed_at)
    score = int(dt.timestamp() * 1000)  # epoch milliseconds
    payload = {
        "processor": processor,
        "amount": str(amount),
    }
    if correlation_id is not None:
        payload["correlationId"] = correlation_id
    member = orjson.dumps(payload)
    redis = await get_redis()
    await redis.zadd(ZSET_KEY, {member: score})


async def summarize_range(from_dt: datetime, to_dt: datetime) -> Dict[str, Dict[str, float | int]]:
    f = _utc(from_dt)
    t = _utc(to_dt)
    min_score = int(f.timestamp() * 1000)
    max_score = int(t.timestamp() * 1000)

    redis = await get_redis()
    members = await redis.zrangebyscore(ZSET_KEY, min_score, max_score)

    total_default_count = 0
    total_fallback_count = 0
    total_default_sum = Decimal(0)
    total_fallback_sum = Decimal(0)

    for m in members:
        try:
            data = orjson.loads(m)
            proc = data.get("processor")
            amt = Decimal(str(data.get("amount", "0")))
            if proc == "default":
                total_default_count += 1
                total_default_sum += amt
            elif proc == "fallback":
                total_fallback_count += 1
                total_fallback_sum += amt
        except Exception:
            continue

    return {
        "default": {
            "totalRequests": total_default_count,
            "totalAmount": float(total_default_sum),
        },
        "fallback": {
            "totalRequests": total_fallback_count,
            "totalAmount": float(total_fallback_sum),
        },
    }


