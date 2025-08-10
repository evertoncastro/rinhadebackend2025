import os
import orjson
import asyncio
import signal
import socket
from typing import Any, Dict, List, Tuple

from .stream import (
    get_redis,
    ensure_stream_exists,
    PAYMENTS_STREAM,
    PAYMENTS_CONSUMER_GROUP,
)
from .services import payment_service


CONSUMER_NAME = os.getenv("WORKER_CONSUMER_NAME") or socket.gethostname()
READ_COUNT = int(os.getenv("WORKER_READ_COUNT", "128"))
READ_BLOCK_MS = int(os.getenv("WORKER_READ_BLOCK_MS", "2000"))
CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "128"))


def _setup_signals(loop: asyncio.AbstractEventLoop) -> None:
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(_stop()))
        except NotImplementedError:
            print(f"Signal {sig} not supported")
            pass


_shutdown_event = asyncio.Event()


async def _stop() -> None:
    _shutdown_event.set()


async def _handle_messages(entries: List[Tuple[str, List[Tuple[str, Dict[str, Any]]]]]) -> None:
    if not entries:
        return
    redis = await get_redis()
    ack_ids: List[str] = []
    sem = asyncio.Semaphore(CONCURRENCY)

    async def handle_one(message_id: str, fields: Dict[str, Any], stream_name: str) -> None:
        async with sem:
            try:
                payload_raw = fields.get(b"data")
                if payload_raw is None:
                    raise Exception("Payload raw is None")
                payment_data = orjson.loads(payload_raw)
                processed = await payment_service.process_payment(payment_data)
                if processed:
                    ack_ids.append(message_id)
            except Exception as exc:
                print(f"Worker error processing message {message_id}: {exc}")

    tasks: List[asyncio.Task] = []
    for stream_name, messages in entries:
        for message_id, fields in messages:
            tasks.append(asyncio.create_task(handle_one(message_id, fields, stream_name)))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
        if ack_ids:
            await redis.xack(PAYMENTS_STREAM, PAYMENTS_CONSUMER_GROUP, *ack_ids)


async def run_worker() -> None:
    await ensure_stream_exists()
    redis = await get_redis()
    print(
        f"Worker started consumer={CONSUMER_NAME} group={PAYMENTS_CONSUMER_GROUP} stream={PAYMENTS_STREAM}"
    )
    while not _shutdown_event.is_set():
        try:
            entries = await redis.xreadgroup(
                groupname=PAYMENTS_CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={PAYMENTS_STREAM: ">"},
                count=READ_COUNT,
                block=READ_BLOCK_MS,
            )
            await _handle_messages(entries)
        except Exception as exc:
            print(f"Worker loop error: {exc}")
            await asyncio.sleep(1)

    print("Worker shutting down...")


def main() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _setup_signals(loop)
    try:
        loop.run_until_complete(run_worker())
    finally:
        loop.run_until_complete(asyncio.sleep(0))
        loop.close()


if __name__ == "__main__":
    main()


