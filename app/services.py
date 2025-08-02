from datetime import datetime, timezone
from .models import PaymentRequest, PaymentProcessorRequest
from .db import save_payment
from .client import default_processor, fallback_processor


class PaymentService:

    async def process_payment(self, payment: PaymentRequest) -> bool:
        requested_at = datetime.now(timezone.utc)
        processor_request = PaymentProcessorRequest(
            correlationId=payment.correlationId,
            amount=payment.amount,
            requestedAt=requested_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        )
        processed = await default_processor.process_payment(processor_request)
        internal_id = await save_payment(
            payment.correlationId, 
            payment.amount, 
            requested_at,
            "default"
        )
        print(f"Payment saved with internal ID: {internal_id}")
        return processed

payment_service = PaymentService()
        