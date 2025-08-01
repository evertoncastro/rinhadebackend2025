import httpx
import os
from datetime import datetime, timezone
from fastapi import HTTPException
from .models import PaymentRequest, PaymentProcessorRequest
from .db import save_payment

class PaymentService:
    def __init__(self):
        self.default_url = os.getenv("PROCESSOR_DEFAULT_URL", "http://payment-processor-default:8080")
        self.timeout = 10.0

    async def process_payment(self, payment: PaymentRequest):
        requested_at = datetime.now(timezone.utc)
        processor_request = PaymentProcessorRequest(
            correlationId=payment.correlationId,
            amount=payment.amount,
            requestedAt=requested_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.default_url}/payments",
                    json=processor_request.model_dump(),
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                print(f"Payment processor successful response: {response.json()}")
                internal_id = await save_payment(
                    payment.correlationId, 
                    payment.amount, 
                    requested_at,
                    "default"
                )
                print(f"Payment saved: {internal_id}")
                return response
        except httpx.HTTPStatusError as e:
            if 400 <= e.response.status_code <= 499:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Payment processors error: {e.response.json()["message"]}"
                )
            raise HTTPException(
                status_code=503,
                detail=f"Payment processors error: {e}"
            )

payment_service = PaymentService()
        