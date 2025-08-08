import os
import json
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
from .models import PaymentProcessorRequest


CONSUMER_NAME = os.getenv("WORKER_CONSUMER_NAME") or socket.gethostname()
READ_COUNT = int(os.getenv("WORKER_READ_COUNT", "10"))
READ_BLOCK_MS = int(os.getenv("WORKER_READ_BLOCK_MS", "5000"))


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
    for stream_name, messages in entries:
        for message_id, fields in messages:
            try:
                payload_raw = fields.get("data")
                if payload_raw:
                    payload = json.loads(payload_raw)
                else:
                    payload = fields

                processor_req = PaymentProcessorRequest(
                    correlationId=str(payload["correlationId"]),
                    amount=str(payload["amount"]),
                    requestedAt=str(payload["requestedAt"]),
                )

                processed = await payment_service.process_payment(processor_req)
                if processed:
                    await redis.xack(PAYMENTS_STREAM, PAYMENTS_CONSUMER_GROUP, message_id)
                print(f"Worker {"processed" if processed else "failed"} message {message_id}")
            except Exception as exc:
                print(f"Worker error processing message {message_id}: {exc}")


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


