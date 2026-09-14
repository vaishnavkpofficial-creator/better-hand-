from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class BystanderAccessCode:
    id: Optional[str] = None
    code: str = ""
    hospital_id: str = ""
    blood_group: str = ""
    patient_name: str = ""
    patient_ward: str = ""
    patient_room: str = ""
    is_used: bool = False
    used_request_id: Optional[str] = None
    is_revoked: bool = False              # NEW
    revoked_at: Optional[datetime] = None # NEW
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BystanderPayment:
    id: Optional[str] = None
    access_code_id: str = ""
    razorpay_order_id: str = ""
    razorpay_payment_id: Optional[str] = None
    amount_paise: int = 0              # Razorpay works in the smallest currency unit (paise, not rupees)
    status: str = "created"            # "created", "paid", "failed"
    created_at: datetime = field(default_factory=datetime.utcnow)
    paid_at: Optional[datetime] = None