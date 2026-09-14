import hmac
import hashlib
import httpx
from app.core.config import settings

RAZORPAY_BASE_URL = "https://api.razorpay.com/v1"


async def create_razorpay_order(amount_paise: int, receipt: str) -> dict:
    """
    Creates an order on Razorpay's side. `receipt` is just your own
    reference string (we'll use the access code's id) so you can trace
    a payment back to what it was for.
    """
    payload = {
        "amount": amount_paise,     # Razorpay always wants paise, e.g. 5000 = ₹50.00
        "currency": "INR",
        "receipt": receipt,
        "payment_capture": 1        # auto-capture the payment once authorized
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{RAZORPAY_BASE_URL}/orders",
            json=payload,
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
            timeout=15.0
        )
        resp.raise_for_status()
        return resp.json()   # contains "id" (the order_id), "amount", "currency", etc.


def verify_razorpay_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """
    Recomputes the signature Razorpay *should* have sent, using your
    secret key, and compares it to what the client actually sent.
    If they don't match, the payment claim is not trustworthy.
    """
    body = f"{order_id}|{payment_id}"
    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)