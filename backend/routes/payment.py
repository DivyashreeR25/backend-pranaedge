from fastapi import APIRouter, Depends
from backend.models.payment import PaymentRequest, PaymentResponse
from backend.db.mongo import payments_collection
from datetime import datetime
import random, string

from backend.utils.auth import get_current_user

router = APIRouter()

MERCHANT_UPI = "yourmerchant@upi"   # 👈 replace with your UPI
MERCHANT_NAME = "PranaEdge"


def generate_txn_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))


@router.post("/pay", response_model=PaymentResponse)
async def create_payment(
    request: PaymentRequest,
    user_id: str = Depends(get_current_user)
):
    txn_id = generate_txn_id()

    # 🔥 Create UPI URL
    upi_url = (
        f"upi://pay?"
        f"pa={MERCHANT_UPI}&"
        f"pn={MERCHANT_NAME}&"
        f"am={request.amount}&"
        f"cu=INR&"
        f"tn={request.plan}_{txn_id}"
    )

    payment_data = {
        "user_id": user_id,
        "plan": request.plan,
        "amount": request.amount,
        "transaction_id": txn_id,
        "status": "PENDING",
        "timestamp": datetime.utcnow()
    }

    await payments_collection.insert_one(payment_data)

    return PaymentResponse(
        payment_url=upi_url,
        transaction_id=txn_id,
        status="PENDING",
        message="Open this URL to complete payment"
    )

@router.post("/pay/verify/{txn_id}")
async def verify_payment(txn_id: str):
    status = "SUCCESS" if random.random() > 0.2 else "FAILED"

    await payments_collection.update_one(
        {"transaction_id": txn_id},
        {"$set": {"status": status}}
    )

    return {
        "transaction_id": txn_id,
        "status": status
    }