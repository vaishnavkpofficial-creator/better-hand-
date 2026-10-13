from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BystanderCodeCreateDTO(BaseModel):
    blood_group: Optional[str] = ""
    patient_name: Optional[str] = ""
    patient_ward: Optional[str] = ""
    patient_room: Optional[str] = ""
    expires_in_hours: Optional[int] = 24


class BystanderCodeResponse(BaseModel):
    id: str
    code: str
    expires_at: Optional[datetime]


class BystanderOrderRequestDTO(BaseModel):
    code: str


class BystanderOrderResponse(BaseModel):
    order_id: str
    amount_paise: int
    currency: str
    razorpay_key_id: str


class BystanderSubmitRequestDTO(BaseModel):
    code: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

    blood_group: str
    units_needed: int = 1
    urgency: str = "normal"
    note: Optional[str] = ""

    patient_name: Optional[str] = ""
    patient_age: Optional[int] = None
    patient_condition: Optional[str] = ""
    patient_ward: Optional[str] = ""
    patient_room: Optional[str] = ""
    patient_bed: Optional[str] = ""
    ward_contact_person: Optional[str] = ""
    ward_contact_phone: Optional[str] = ""
    bystander_name: str
    bystander_phone: str

    patient_state: Optional[str] = ""
    patient_district: Optional[str] = ""
    patient_local_body_type: Optional[str] = ""
    patient_local_body_name: Optional[str] = ""
    patient_ward_number: Optional[str] = ""
    search_radius_km: Optional[int] = 50