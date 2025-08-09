import httpx
import os
from enum import Enum
from fastapi import HTTPException

class Processor(Enum):
    DEFAULT = "default"
    FALLBACK = "fallback"


DEFAULT_URL = os.getenv("PROCESSOR_DEFAULT_URL", "http://payment-processor-default:8080")
FALLBACK_URL = os.getenv("PROCESSOR_FALLBACK_URL", "http://payment-processor-fallback:8080")


class ProcessorAPIClient:
    def __init__(self, processor: Processor = Processor.DEFAULT):
        self.url = DEFAULT_URL if processor == Processor.DEFAULT else FALLBACK_URL
        self.processor = processor
        connect_timeout = float(os.getenv("HTTPX_CONNECT_TIMEOUT", "1.0"))
        read_timeout = float(os.getenv("HTTPX_READ_TIMEOUT", "5.0"))
        write_timeout = float(os.getenv("HTTPX_WRITE_TIMEOUT", "5.0"))
        pool_timeout = float(os.getenv("HTTPX_POOL_TIMEOUT", "5.0"))
        max_connections = int(os.getenv("HTTPX_MAX_CONNECTIONS", "200"))
        max_keepalive = int(os.getenv("HTTPX_MAX_KEEPALIVE", "50"))
        self.timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=write_timeout,
            pool=pool_timeout,
        )
        self.limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive,
        )
        self.client = httpx.AsyncClient(timeout=self.timeout, limits=self.limits)

    async def process_payment(self, payment_data: dict) -> bool:
        try:
            response = await self.client.post(
                f"{self.url}/payments",
                json=payment_data,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return True
        except httpx.TimeoutException:
            print(f"Payment processor ({self.processor}) timeout")
            raise
        except httpx.HTTPStatusError as e:
            if 400 <= e.response.status_code <= 499:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Payment processor ({self.processor}) error: {e.response.json().get('message', str(e))}"
                )
            raise HTTPException(
                status_code=500,
                detail=f"Payment processor ({self.processor}) error: {e}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Payment processor ({self.processor}) connection error: {e}"
            )

    async def aclose(self) -> None:
        try:
            await self.client.aclose()
        except Exception:
            pass

default_processor = ProcessorAPIClient(Processor.DEFAULT) 
fallback_processor = ProcessorAPIClient(Processor.FALLBACK)