from fastapi import FastAPI, HTTPException, Response, Query
from typing import Optional
from datetime import datetime, timezone
from .services import payment_service
from .stream import ensure_stream_exists, close_redis


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
    from_datetime: Optional[str] = Query(None, description="Start datetime in ISO format (UTC)"),
    to_datetime: Optional[str] = Query(None, description="End datetime in ISO format (UTC)")
):
    from_dt, to_dt = None, None
    if from_datetime:
        try:
            from_dt = datetime.fromisoformat(from_datetime.replace('Z', '+00:00'))
            from_dt = from_dt.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid from_datetime format. Use ISO format (e.g., 2020-07-10T12:34:56.000Z)"
            )
    
    if to_datetime:
        try:
            to_dt = datetime.fromisoformat(to_datetime.replace('Z', '+00:00'))
            to_dt = to_dt.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid to_datetime format. Use ISO format (e.g., 2020-07-10T12:34:56.000Z)"
            )
    try:
        return {
            "default": {
                "totalRequests": 0,
                "totalAmount": 0
            },
            "fallback": {
                "totalRequests": 0,
                "totalAmount": 0
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving payment summary: {str(e)}"
        )


@app.post("/purge-payments", status_code=204)
async def purge_payments_endpoint():
    try:
        deleted_count = await purge_payments()
        return {"deleted_count": deleted_count}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error purging payments: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True) 