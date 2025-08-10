from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
import os
from decimal import Decimal, ROUND_HALF_UP

from .stream import get_redis


INDEX_SECONDS_KEY = "payments:agg:index:s"  # ZSET: score = epoch second, member = YYYYMMDDHHMMSS
AGG_SCALE = int(os.getenv("AGG_SCALE", "1000000"))  # unidades por moeda (ex.: 1e6 para micros)


def _normalize_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _second_id_and_score(dt: datetime) -> Tuple[str, int]:
    dt = _normalize_utc(dt)
    second_id = dt.strftime("%Y%m%d%H%M%S")
    epoch_sec = int(dt.timestamp())
    return second_id, epoch_sec


async def incr_agg(processor: str, amount: Any, requested_at: datetime) -> None:
    """Increment per-second aggregates for the given processor and amount.

    - amount pode ser str/Decimal/float/int. Convertemos para inteiro em 'AGG_SCALE' unidades.
    """
    second_id, epoch_sec = _second_id_and_score(requested_at)
    key = f"payments:agg:s:{second_id}"

    field_count = f"{processor}_count"
    # Mantemos o nome 'sum_cents' por compatibilidade; a unidade real é AGG_SCALE
    field_sum = f"{processor}_sum_cents"

    # Conversão do amount para inteiro na escala AGG_SCALE
    dec = Decimal(str(amount))
    amount_units = int((dec * Decimal(AGG_SCALE)).to_integral_value(rounding=ROUND_HALF_UP))

    redis = await get_redis()
    pipe = redis.pipeline()
    pipe.hincrby(key, field_count, 1)
    pipe.hincrby(key, field_sum, amount_units)
    pipe.zadd(INDEX_SECONDS_KEY, {second_id: epoch_sec}, nx=True)
    await pipe.execute()


async def summarize(from_dt: datetime, to_dt: datetime) -> Dict[str, Dict[str, int]]:
    """Return summary between from_dt and to_dt (inclusive) as integer cents.

    Shape: {
      "default": {"totalRequests": int, "totalAmount": int},
      "fallback": {"totalRequests": int, "totalAmount": int},
    }
    """
    from_dt = _normalize_utc(from_dt)
    to_dt = _normalize_utc(to_dt)

    from_sec = int(from_dt.timestamp())
    to_sec = int(to_dt.timestamp())

    redis = await get_redis()
    # Get all second IDs in range
    second_ids: List[bytes] = await redis.zrangebyscore(INDEX_SECONDS_KEY, from_sec, to_sec)
    result = {
        "default": {"totalRequests": 0, "totalAmount": 0},
        "fallback": {"totalRequests": 0, "totalAmount": 0},
    }
    if not second_ids:
        return result

    pipe = redis.pipeline()
    keys = [f"payments:agg:s:{sid.decode() if isinstance(sid, (bytes, bytearray)) else sid}" for sid in second_ids]
    fields = ["default_count", "default_sum_cents", "fallback_count", "fallback_sum_cents"]
    for key in keys:
        pipe.hmget(key, *fields)  # type: ignore[arg-type]
    rows = await pipe.execute()

    for row in rows:
        dcnt, dsum, fcnt, fsum = row
        if isinstance(dcnt, (bytes, bytearray)):
            dcnt = int(dcnt or b"0")
        else:
            dcnt = int(dcnt or 0)
        if isinstance(dsum, (bytes, bytearray)):
            dsum = int(dsum or b"0")
        else:
            dsum = int(dsum or 0)
        if isinstance(fcnt, (bytes, bytearray)):
            fcnt = int(fcnt or b"0")
        else:
            fcnt = int(fcnt or 0)
        if isinstance(fsum, (bytes, bytearray)):
            fsum = int(fsum or b"0")
        else:
            fsum = int(fsum or 0)

        result["default"]["totalRequests"] += dcnt
        result["default"]["totalAmount"] += dsum
        result["fallback"]["totalRequests"] += fcnt
        result["fallback"]["totalAmount"] += fsum

    return result


