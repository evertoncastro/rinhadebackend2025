from datetime import datetime, timezone
from .models import PaymentRequest, PaymentProcessorRequest
from .db import save_payment
from .stream import append_payment_to_stream
from .client import default_processor, fallback_processor
from httpx import TimeoutException
from fastapi.exceptions import HTTPException


class PaymentService:

    async def process_payment(self, payment: PaymentRequest) -> bool:
        requested_at = datetime.now(timezone.utc)
        processor_request = PaymentProcessorRequest(
            correlationId=payment.correlationId,
            amount=str(payment.amount),
            requestedAt=requested_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        )
        # try:
        #     processed = await default_processor.process_payment(processor_request)
        #     processed_by = default_processor.processor.value
        # except HTTPException as e:
        #     print(f"")
        #     if e.status_code != 500:
        #         raise e
        #     processed = await fallback_processor.process_payment(processor_request)
        #     processed_by = fallback_processor.processor.value
        # internal_id = await save_payment(
        #     payment.correlationId, 
        #     payment.amount, 
        #     requested_at,
        #     processed_by
        # )
        # print(f"Payment saved with internal ID: {internal_id}")
        # enqueue to redis stream for async processing by worker(s)
        try:
            message_id = await append_payment_to_stream({
                "correlationId": payment.correlationId,
                "amount": str(payment.amount),
                "requestedAt": processor_request.requestedAt
            })
            print(f"Payment enqueued to stream with message ID: {message_id}")
        except Exception as e:
            print(f"Failed to enqueue payment to stream: {e}")
        return True

payment_service = PaymentService()
        