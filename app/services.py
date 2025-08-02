from datetime import datetime, timezone
from .models import PaymentRequest, PaymentProcessorRequest
from .db import save_payment
from .client import default_processor, fallback_processor
from httpx import TimeoutException


class PaymentService:

    async def process_payment(self, payment: PaymentRequest) -> bool:
        requested_at = datetime.now(timezone.utc)
        processor_request = PaymentProcessorRequest(
            correlationId=payment.correlationId,
            amount=payment.amount,
            requestedAt=requested_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        )
        try:
            processed = await default_processor.process_payment(processor_request)
            processed_by = default_processor.processor.value
        except TimeoutException:
            processed = await fallback_processor.process_payment(processor_request)
            processed_by = fallback_processor.processor.value
        internal_id = await save_payment(
            payment.correlationId, 
            payment.amount, 
            requested_at,
            processed_by
        )
        print(f"Payment saved with internal ID: {internal_id}")
        return processed

payment_service = PaymentService()
        