from pydantic import BaseModel

class PaymentRequest(BaseModel):
    plan: str
    amount: float
    upi_id: str  # user's UPI (optional for simulation)

class PaymentResponse(BaseModel):
    payment_url: str
    transaction_id: str
    status: str
    message: str