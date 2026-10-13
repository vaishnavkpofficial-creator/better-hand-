from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from app.infrastructure.database.mongodb import db
from app.domain.entities.bystander import BystanderAccessCode, BystanderPayment
from app.domain.repositories.bystander_repo import BystanderAccessCodeRepository, BystanderPaymentRepository


def map_code_to_entity(doc: dict) -> BystanderAccessCode:
    return BystanderAccessCode(
        id=str(doc["_id"]),
        code=doc.get("code", ""),
        hospital_id=str(doc.get("hospital_id", "")),
        blood_group=doc.get("blood_group", ""),
        patient_name=doc.get("patient_name", ""),
        patient_ward=doc.get("patient_ward", ""),
        patient_room=doc.get("patient_room", ""),
        is_used=doc.get("is_used", False),
        used_request_id=str(doc.get("used_request_id")) if doc.get("used_request_id") else None,
        is_revoked=doc.get("is_revoked", False),
        revoked_at=doc.get("revoked_at"),
        expires_at=doc.get("expires_at"),
        created_at=doc.get("created_at", datetime.utcnow())
    )

def map_code_to_db(entity: BystanderAccessCode) -> dict:
    data = {
        "code": entity.code,
        "hospital_id": ObjectId(entity.hospital_id) if entity.hospital_id else "",
        "blood_group": entity.blood_group,
        "patient_name": entity.patient_name,
        "patient_ward": entity.patient_ward,
        "patient_room": entity.patient_room,
        "is_used": entity.is_used,
        "used_request_id": ObjectId(entity.used_request_id) if entity.used_request_id else None,
        "is_revoked": entity.is_revoked,
        "revoked_at": entity.revoked_at,
        "expires_at": entity.expires_at,
        "created_at": entity.created_at
    }
    if entity.id:
        data["_id"] = ObjectId(entity.id)
    return data


def map_payment_to_entity(doc: dict) -> BystanderPayment:
    return BystanderPayment(
        id=str(doc["_id"]),
        access_code_id=str(doc.get("access_code_id", "")),
        razorpay_order_id=doc.get("razorpay_order_id", ""),
        razorpay_payment_id=doc.get("razorpay_payment_id"),
        amount_paise=doc.get("amount_paise", 0),
        status=doc.get("status", "created"),
        created_at=doc.get("created_at", datetime.utcnow()),
        paid_at=doc.get("paid_at")
    )

def map_payment_to_db(entity: BystanderPayment) -> dict:
    data = {
        "access_code_id": ObjectId(entity.access_code_id) if entity.access_code_id else "",
        "razorpay_order_id": entity.razorpay_order_id,
        "razorpay_payment_id": entity.razorpay_payment_id,
        "amount_paise": entity.amount_paise,
        "status": entity.status,
        "created_at": entity.created_at,
        "paid_at": entity.paid_at
    }
    if entity.id:
        data["_id"] = ObjectId(entity.id)
    return data


class MongoBystanderAccessCodeRepository(BystanderAccessCodeRepository):
    async def create(self, code: BystanderAccessCode) -> BystanderAccessCode:
        doc = map_code_to_db(code)
        result = await db.db.bystander_access_codes.insert_one(doc)
        code.id = str(result.inserted_id)
        return code

    async def list_by_hospital(self, hospital_id: str) -> List[BystanderAccessCode]:
        docs = await db.db.bystander_access_codes.find(
            {"hospital_id": ObjectId(hospital_id)}
        ).sort("created_at", -1).to_list(length=500)
        return [map_code_to_entity(doc) for doc in docs]
    
    async def get_by_code(self, code: str) -> Optional[BystanderAccessCode]:
        doc = await db.db.bystander_access_codes.find_one({"code": code})
        return map_code_to_entity(doc) if doc else None

    async def get_by_id(self, code_id: str) -> Optional[BystanderAccessCode]:
        try:
            doc = await db.db.bystander_access_codes.find_one({"_id": ObjectId(code_id)})
            return map_code_to_entity(doc) if doc else None
        except Exception:
            return None

    async def update(self, code: BystanderAccessCode) -> BystanderAccessCode:
        doc = map_code_to_db(code)
        await db.db.bystander_access_codes.replace_one({"_id": ObjectId(code.id)}, doc)
        return code


class MongoBystanderPaymentRepository(BystanderPaymentRepository):
    async def create(self, payment: BystanderPayment) -> BystanderPayment:
        doc = map_payment_to_db(payment)
        result = await db.db.bystander_payments.insert_one(doc)
        payment.id = str(result.inserted_id)
        return payment

    async def get_by_order_id(self, razorpay_order_id: str) -> Optional[BystanderPayment]:
        doc = await db.db.bystander_payments.find_one({"razorpay_order_id": razorpay_order_id})
        return map_payment_to_entity(doc) if doc else None

    async def update(self, payment: BystanderPayment) -> BystanderPayment:
        doc = map_payment_to_db(payment)
        await db.db.bystander_payments.replace_one({"_id": ObjectId(payment.id)}, doc)
        return payment