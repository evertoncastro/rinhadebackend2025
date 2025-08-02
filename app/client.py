import httpx
import os
from enum import Enum
from fastapi import HTTPException
from .models import PaymentProcessorRequest


class Processor(Enum):
    DEFAULT = "default"
    FALLBACK = "fallback"


DEFAULT_URL = os.getenv("PROCESSOR_DEFAULT_URL", "http://payment-processor-default:8080")
FALLBACK_URL = os.getenv("PROCESSOR_FALLBACK_URL", "http://payment-processor-fallback:8080")


class ProcessorAPIClient:
    def __init__(self, processor: Processor = Processor.DEFAULT):
        self.url = DEFAULT_URL if processor == Processor.DEFAULT else FALLBACK_URL
        self.processor = processor
        self.timeout = 2.0

    async def process_payment(self, processor_request: PaymentProcessorRequest) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.url}/payments",
                    json=processor_request.model_dump(),
                    headers={"Content-Type": "application/json"},
                    timeout=httpx.Timeout(self.timeout)
                )
                response.raise_for_status()
                print(f"Payment processor ({self.processor}) successful response: {response.json()}")
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
                status_code=503,
                detail=f"Payment processor ({self.processor}) error: {e}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Payment processor ({self.processor}) connection error: {e}"
            )

default_processor = ProcessorAPIClient(Processor.DEFAULT) 
fallback_processor = ProcessorAPIClient(Processor.FALLBACK)