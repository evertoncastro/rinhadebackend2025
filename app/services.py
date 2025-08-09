from datetime import datetime, timezone
from .models import PaymentProcessorRequest
from .stream import append_payment_to_stream
from .client import default_processor, fallback_processor
from fastapi.exceptions import HTTPException


class PaymentService:

    async def receive_payment(self, payment: dict) -> bool:
        requested_at = datetime.now(timezone.utc)
        payment["requestedAt"] = requested_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        try:
            message_id = await append_payment_to_stream(payload=payment)
            print(f"Payment enqueued to stream with message ID: {message_id}")
        except Exception as e:
            raise Exception(f"Failed to enqueue payment to stream: {e}")
        return True

    async def process_payment(self, payment_processor_req: PaymentProcessorRequest) -> bool:
        try:
            processed = await default_processor.process_payment(payment_processor_req)
            processed_by = default_processor.processor.value
        except HTTPException as e:
            print(f"")
            if e.status_code != 500:
                raise e
            processed = await fallback_processor.process_payment(payment_processor_req)
            processed_by = fallback_processor.processor.value
        print(f"Payment processed by {processed_by}")
        return processed

payment_service = PaymentService()
        