import os
import orjson
import asyncio
import signal
import socket
import logging
from typing import Any, Dict, List, Tuple, Optional

from .stream import (
    get_redis,
    ensure_stream_exists,
    PAYMENTS_STREAM,
    PAYMENTS_CONSUMER_GROUP,
)
from .services import payment_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONSUMER_NAME = os.getenv("WORKER_CONSUMER_NAME") or socket.gethostname()
READ_COUNT = int(os.getenv("WORKER_READ_COUNT", "128"))
READ_BLOCK_MS = int(os.getenv("WORKER_READ_BLOCK_MS", "2000"))
CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "128"))

logger.info(f"Worker starting with CONSUMER_NAME={CONSUMER_NAME}, READ_COUNT={READ_COUNT}, CONCURRENCY={CONCURRENCY}")

def _setup_signals(loop: asyncio.AbstractEventLoop) -> None:
    logger.info("Setting up signal handlers")
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(_stop()))
            logger.info(f"Signal handler added for {sig}")
        except NotImplementedError:
            logger.warning(f"Signal {sig} not supported")
            pass


_shutdown_event = asyncio.Event()
_worker_task: Optional[asyncio.Task] = None


async def _stop() -> None:
    logger.info("Shutdown signal received")
    _shutdown_event.set()


async def _handle_messages(entries: List[Tuple[str, List[Tuple[str, Dict[str, Any]]]]]) -> None:
    if not entries:
        return
    logger.info(f"Processing {len(entries)} message entries")
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
                logger.error(f"Worker error processing message {message_id}: {exc}")

    tasks: List[asyncio.Task] = []
    for stream_name, messages in entries:
        for message_id, fields in messages:
            tasks.append(asyncio.create_task(handle_one(message_id, fields, stream_name)))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
        if ack_ids:
            logger.info(f"Acknowledging {len(ack_ids)} messages")
            await redis.xack(PAYMENTS_STREAM, PAYMENTS_CONSUMER_GROUP, *ack_ids)


async def run_worker() -> None:
    logger.info("Starting worker main loop")
    try:
        logger.info("Ensuring stream exists...")
        await ensure_stream_exists()
        logger.info("Stream ensured successfully")
        
        logger.info("Getting Redis connection...")
        redis = await get_redis()
        logger.info("Redis connection established")
        
        logger.info(
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
                logger.error(f"Worker loop error: {exc}", exc_info=True)
                await asyncio.sleep(1)

        logger.info("Worker shutting down...")
    except Exception as exc:
        logger.error(f"Critical error in run_worker: {exc}", exc_info=True)
        raise


def start_in_current_loop() -> asyncio.Task:
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(run_worker())
        logger.info("Background worker task created")
    return _worker_task


async def stop_worker() -> None:
    await _stop()
    if _worker_task is not None:
        try:
            await _worker_task
        except Exception:
            pass


def main() -> None:
    logger.info("Worker main function started")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.info("Event loop created and set")
        
        _setup_signals(loop)
        logger.info("Signal handlers configured")
        
        logger.info("Starting worker loop...")
        loop.run_until_complete(run_worker())
        logger.info("Worker loop completed")
    except Exception as exc:
        logger.error(f"Critical error in main: {exc}", exc_info=True)
        raise
    finally:
        logger.info("Cleaning up...")
        try:
            loop.run_until_complete(asyncio.sleep(0))
        except:
            pass
        loop.close()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    logger.info("Worker script started")
    main()


