from pydantic import BaseModel, Field
from typing import Annotated

class PaymentRequest(BaseModel):
    correlationId: Annotated[str, Field(min_length=1, max_length=100, description="ID de correlação único")]
    amount: Annotated[float, Field(gt=0, description="Valor do pagamento em reais")]

    class Config:
        validate_assignment = True
        str_strip_whitespace = True

class PaymentProcessorRequest(BaseModel):
    correlationId: str
    amount: float
    requestedAt: str 