from datetime import datetime, timezone
from .models import PaymentProcessorRequest
from .stream import append_payment_to_stream
from .client import default_processor, fallback_processor
from fastapi.exceptions import HTTPException


class PaymentService:

    async def receive_payment(self, payment: dict) -> bool:
        try:
            await append_payment_to_stream(payload=payment)
        except Exception as e:
            raise Exception(f"Failed to enqueue payment to stream: {e}")
        return True

    async def process_payment(self, payment_data: dict) -> bool:
        requested_at = datetime.now(timezone.utc)
        payment_data["requestedAt"] = requested_at.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        try:
            processed = await default_processor.process_payment(payment_data)
            # processed_by = default_processor.processor.value
        except HTTPException as e:
            if e.status_code != 500:
                raise e
            processed = await fallback_processor.process_payment(payment_data)
            # processed_by = fallback_processor.processor.value
        return processed

payment_service = PaymentService()
        