from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Annotated
import uuid

app = FastAPI(
    title="Rinha de Backend 2025",
    description="API de pagamentos com alta performance",
    version="1.0.0"
)

class PaymentRequest(BaseModel):
    correlationId: Annotated[str, Field(min_length=1, max_length=100, description="ID de correlação único")]
    amount: Annotated[float, Field(gt=0, description="Valor do pagamento em reais")]

    class Config:
        validate_assignment = True
        str_strip_whitespace = True

@app.post("/payments", status_code=200)
async def create_payment(payment: PaymentRequest):
    try:
        uuid.UUID(payment.correlationId)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="correlationId deve ser um UUID válido"
        )
    
    return {
        "status": "success",
        "message": "Pagamento processado com sucesso",
        "correlationId": payment.correlationId,
        "amount": payment.amount
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True) 