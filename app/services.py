from datetime import datetime, timezone
from .stream import append_payment_to_stream
from .client import default_processor, fallback_processor
from fastapi.exceptions import HTTPException
from .zstore import add_processed


class PaymentService:

    async def receive_payment(self, payment: dict) -> None:
        await append_payment_to_stream(payload=payment)

    async def process_payment(self, payment_data: dict) -> bool:
        requested_at = datetime.now(timezone.utc)
        payment_data["requestedAt"] = requested_at.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        processed_by = "default"
        try:
            processed = await default_processor.process_payment(payment_data)
            processed_by = "default"
        except HTTPException as e:
            if e.status_code != 500:
                raise e
            processed = await fallback_processor.process_payment(payment_data)
            processed_by = "fallback"
        if processed:
            await add_processed(processed_by, payment_data["amount"], requested_at, payment_data.get("correlationId"))
        return processed

payment_service = PaymentService()
        