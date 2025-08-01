from fastapi import FastAPI, HTTPException, Response
import uuid
from .models import PaymentRequest
from .services import payment_service
from .db import init_db, close_pool


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True) 