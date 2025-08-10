from fastapi import FastAPI, HTTPException, Response, Query
from typing import Optional
from datetime import datetime, timezone
from decimal import Decimal
import os
from .services import payment_service
from .stream import ensure_stream_exists, close_redis
from .zstore import summarize_range


app = FastAPI(
    title="Rinha de Backend 2025",
    description="API de pagamentos com alta performance",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    await ensure_stream_exists()

@app.on_event("shutdown")
async def shutdown_event():
    await close_redis()


@app.post("/payments", status_code=204)
async def create_payment(payment: dict):
    try:
        await payment_service.receive_payment(payment)
        return Response(status_code=204)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing payment: {str(e)}"
        )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/payments-summary")
async def get_payments_summary_endpoint(
    from_datetime: str = Query(..., description="Start datetime in ISO format (UTC)", alias="from"),
    to_datetime: str = Query(..., description="End datetime in ISO format (UTC)", alias="to")
):
    if not from_datetime:
        from_datetime = "2025-01-01T00:00:00.000Z"
    if not to_datetime:
        to_datetime = "2025-12-31T00:00:00.000Z"

    from_dt = datetime.fromisoformat(from_datetime.replace('Z', '+00:00')).astimezone(timezone.utc)
    to_dt = datetime.fromisoformat(to_datetime.replace('Z', '+00:00')).astimezone(timezone.utc)
    
    try:
        return await summarize_range(from_dt, to_dt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving payment summary: {str(e)}")


@app.post("/purge-payments", status_code=204)
async def purge_payments_endpoint():
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True) 