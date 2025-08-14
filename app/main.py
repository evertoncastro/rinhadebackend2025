from fastapi import FastAPI, HTTPException, Response, Query
from typing import Optional
from datetime import datetime, timezone
from decimal import Decimal
import os
from .services import payment_service
from .stream import ensure_stream_exists, close_redis
from .zstore import summarize_range
from .worker import start_in_current_loop, stop_worker
from .health import start_health_poller, stop_health_poller


app = FastAPI(
    title="Rinha de Backend 2025",
    description="API de pagamentos com alta performance",
    version="1.0.0"
)

_embed_worker = os.getenv("EMBED_WORKER", "false").lower() == "true"
_health_poller_enabled = os.getenv("HEALTH_POLL_ENABLED", "false").lower() == "true"

@app.on_event("startup")
async def startup_event():
    await ensure_stream_exists()
    if _embed_worker:
        start_in_current_loop()
    if _health_poller_enabled:
        start_health_poller()

@app.on_event("shutdown")
async def shutdown_event():
    await close_redis()
    if _embed_worker:
        await stop_worker()
    if _health_poller_enabled:
        await stop_health_poller()


@app.post("/payments", status_code=204)
async def create_payment(payment: dict):
    await payment_service.receive_payment(payment)
    return


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/payments-summary")
async def get_payments_summary_endpoint(
    from_datetime: str = Query(..., description="Start datetime in ISO format (UTC)", alias="from"),
    to_datetime: str = Query(..., description="End datetime in ISO format (UTC)", alias="to")
):
    if not from_datetime:
        from_datetime = "2000-01-01T00:00:00.000Z"
    if not to_datetime:
        to_datetime = "2099-12-31T00:00:00.000Z"

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