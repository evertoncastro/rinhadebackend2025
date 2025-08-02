from fastapi import FastAPI, HTTPException, Response, Query, Header
from typing import Optional
import uuid
from datetime import datetime, timezone
from .models import PaymentRequest
from .services import payment_service
from .db import init_db, close_pool, get_payments_summary, purge_payments


app = FastAPI(
    title="Rinha de Backend 2025",
    description="API de pagamentos com alta performance",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown."""
    await close_pool()


@app.post("/payments", status_code=204)
async def create_payment(payment: PaymentRequest):
    try:
        uuid.UUID(payment.correlationId)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="correlationId deve ser um UUID válido"
        )
    await payment_service.process_payment(payment)
    return Response(status_code=204)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/payments-summary")
async def get_payments_summary_endpoint(
    from_datetime: Optional[str] = Query(None, description="Start datetime in ISO format (UTC)"),
    to_datetime: Optional[str] = Query(None, description="End datetime in ISO format (UTC)")
):
    try:
        from_dt = None
        to_dt = None
        
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
        
        summary = await get_payments_summary(from_dt, to_dt)
        return summary
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving payment summary: {str(e)}"
        )


@app.post("/purge-payments", status_code=204)
async def purge_payments_endpoint(x_rinha_token: Optional[str] = Header(None)):
    """
    Admin endpoint to purge all payments from the database.
    Requires X-Rinha-Token header for authentication.
    """
    # Simple authentication check
    if x_rinha_token != "123":
        raise HTTPException(
            status_code=401,
            detail="Unauthorized. Valid X-Rinha-Token header required."
        )
    
    try:
        deleted_count = await purge_payments()
        return Response(
            status_code=204,
            headers={"X-Deleted-Count": str(deleted_count)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error purging payments: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True) 