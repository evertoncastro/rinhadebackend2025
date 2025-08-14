from datetime import datetime, timezone
from .stream import append_payment_to_stream
from .client import default_processor, fallback_processor, Processor
from fastapi.exceptions import HTTPException
from .zstore import add_processed


class PaymentService:

    async def receive_payment(self, payment: dict) -> None:
        await append_payment_to_stream(payload=payment)

    async def process_payment(self, payment_data: dict) -> bool:
        from .health import get_health_cached
        requested_at = datetime.now(timezone.utc)
        payment_data["requestedAt"] = requested_at.isoformat(timespec="milliseconds").replace("+00:00", "Z")

        default_ok, _ = await get_health_cached(Processor.DEFAULT)
        fallback_ok, _ = await get_health_cached(Processor.FALLBACK)

        chosen = None
        if default_ok is True:
            chosen = "default"
        elif fallback_ok is True:
            chosen = "fallback"
        else:
            # Ambos indisponíveis: evita enviar request para não criar gargalo
            print(f"Both processors are unavailable: {default_ok} {fallback_ok}")
            return False

        try:
            if chosen == "default":
                processed = await default_processor.process_payment(payment_data)
                processed_by = "default"
                print(f"Processed by default: {processed}")
            else:
                processed = await fallback_processor.process_payment(payment_data)
                processed_by = "fallback"
                print(f"Processed by fallback: {processed}")
        except HTTPException as e:
            if e.status_code != 500:
                raise e
            if chosen == "default" and fallback_ok is True:
                processed = await fallback_processor.process_payment(payment_data)
                processed_by = "fallback"
                print(f"Processed by fallback*: {processed}")
            else:
                return False

        if processed:
            await add_processed(processed_by, payment_data["amount"], requested_at, payment_data.get("correlationId"))
        return processed

payment_service = PaymentService()
        