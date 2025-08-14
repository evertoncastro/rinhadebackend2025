import os
import time
import asyncio
from typing import Optional, Tuple

import httpx
import orjson

from .stream import get_redis
from .client import DEFAULT_URL, FALLBACK_URL, Processor

HEALTH_TTL_SECONDS = float(os.getenv("HEALTH_TTL_SECONDS", "5"))

HEALTH_KEY_PREFIX = b"health:"
LOCK_KEY_PREFIX = b"health_lock:"

HTTP_TIMEOUT = httpx.Timeout(connect=0.3, read=0.5, write=0.5, pool=0.5)


def _key_for(proc: Processor) -> bytes:
    name = b"default" if proc == Processor.DEFAULT else b"fallback"
    return HEALTH_KEY_PREFIX + name


def _lock_for(proc: Processor) -> bytes:
    name = b"default" if proc == Processor.DEFAULT else b"fallback"
    return LOCK_KEY_PREFIX + name


def _url_for(proc: Processor) -> str:
    return DEFAULT_URL if proc == Processor.DEFAULT else FALLBACK_URL


async def get_health_cached(proc: Processor) -> Tuple[Optional[bool], Optional[int]]:
    """
    Retorna (is_healthy, minResponseTime). is_healthy=None quando desconhecido.
    Usa Redis como cache compartilhado com TTL e lock distribuído (SET NX PX) para respeitar rate limit.
    """
    redis = await get_redis()
    key = _key_for(proc)
    lock = _lock_for(proc)

    cached = await redis.get(key)
    if cached is not None:
        try:
            data = orjson.loads(cached)
            ts = float(data.get("ts", 0.0))
            if (time.monotonic() - ts) <= HEALTH_TTL_SECONDS:
                failing = bool(data.get("failing"))
                min_rt = int(data.get("minResponseTime", 0))
                return (not failing, min_rt)
        except Exception:
            pass

    # Tenta adquirir lock para atualizar
    locked = await redis.set(lock, b"1", nx=True, px=int(HEALTH_TTL_SECONDS * 1000))
    if locked:
        url = _url_for(proc)
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                resp = await client.get(f"{url}/payments/service-health")
            if resp.status_code == 429:
                print(f"429: {url} {proc.name}")
                payload = {"failing": True, "minResponseTime": 0, "ts": time.monotonic()}
                await redis.set(key, orjson.dumps(payload), ex=int(HEALTH_TTL_SECONDS))
                return (False, 0)
            resp.raise_for_status()
            body = resp.json()
            payload = {
                "failing": bool(body.get("failing", False)),
                "minResponseTime": int(body.get("minResponseTime", 0)),
                "ts": time.monotonic(),
            }
            print(f"200: {url} {proc.name} {payload}")
            await redis.set(key, orjson.dumps(payload), ex=int(HEALTH_TTL_SECONDS))
            return (not payload["failing"], payload["minResponseTime"])
        except Exception:
            payload = {"failing": True, "minResponseTime": 0, "ts": time.monotonic()}
            await redis.set(key, orjson.dumps(payload), ex=int(HEALTH_TTL_SECONDS))
            return (None, None)
        finally:
            pass
    else:
        # Outro nó está atualizando; usa cache (mesmo velho) se existir
        if cached is not None:
            try:
                data = orjson.loads(cached)
                failing = bool(data.get("failing"))
                min_rt = int(data.get("minResponseTime", 0))
                return (not failing, min_rt)
            except Exception:
                pass
        return (None, None)


# Poller opcional (ativado via env; ligar em somente UMA instância)
_poller_task: Optional[asyncio.Task] = None
_stop_event: Optional[asyncio.Event] = None


async def _poll_once() -> None:
    await get_health_cached(Processor.DEFAULT)
    await get_health_cached(Processor.FALLBACK)


async def _poller_loop() -> None:
    assert _stop_event is not None
    while not _stop_event.is_set():
        try:
            await _poll_once()
        except Exception:
            pass
        await asyncio.sleep(HEALTH_TTL_SECONDS)


def start_health_poller() -> asyncio.Task:
    global _poller_task, _stop_event
    if _poller_task is None or _poller_task.done():
        _stop_event = asyncio.Event()
        _poller_task = asyncio.create_task(_poller_loop())
    return _poller_task


async def stop_health_poller() -> None:
    global _poller_task, _stop_event
    if _stop_event is not None:
        _stop_event.set()
    if _poller_task is not None:
        try:
            await _poller_task
        except Exception:
            pass
        _poller_task = None
        _stop_event = None
