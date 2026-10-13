import logging
import secrets
from datetime import datetime, timedelta
from app.core.config import settings
from app.domain.entities.bystander import BystanderAccessCode, BystanderPayment
from app.domain.repositories.bystander_repo import BystanderAccessCodeRepository, BystanderPaymentRepository
from app.domain.repositories.user_repo import HospitalProfileRepository
from app.application.dto.bystander_dto import BystanderCodeCreateDTO, BystanderSubmitRequestDTO
from app.application.dto.donation_dto import BloodRequestCreateDTO
from app.application.use_cases.donation_use_cases import DonationUseCases
from app.infrastructure.external_services.razorpay_service import create_razorpay_order, verify_razorpay_signature

logger = logging.getLogger(__name__)


def _generate_code(length: int = 6) -> str:
    # Uppercase letters + digits, no ambiguous chars (0/O, 1/I) to make it easy to read aloud.
    # secrets (not random) so codes cannot be predicted.
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class BystanderUseCases:
    def __init__(
        self,
        code_repo: BystanderAccessCodeRepository,
        payment_repo: BystanderPaymentRepository,
        hospital_repo: HospitalProfileRepository,
        donation_use_cases: DonationUseCases
    ):
        self.code_repo = code_repo
        self.payment_repo = payment_repo
        self.hospital_repo = hospital_repo
        self.donation_use_cases = donation_use_cases

    async def generate_code(self, hospital_user_id: str, dto: BystanderCodeCreateDTO) -> BystanderAccessCode:
        for _ in range(5):
            candidate = _generate_code()
            existing = await self.code_repo.get_by_code(candidate)
            if not existing:
                break
        else:
            raise ValueError("Could not generate a unique code, try again.")

        requested_hours = dto.expires_in_hours if dto.expires_in_hours is not None else 24
        capped_hours = max(1, min(requested_hours, 168))  # 168 hours = 7 days max

        code = BystanderAccessCode(
            code=candidate,
            hospital_id=hospital_user_id,
            blood_group=dto.blood_group or "",
            patient_name=dto.patient_name or "",
            patient_ward=dto.patient_ward or "",
            patient_room=dto.patient_room or "",
            expires_at=datetime.utcnow() + timedelta(hours=capped_hours)
        )
        return await self.code_repo.create(code)

    async def _get_valid_code(self, code_str: str) -> BystanderAccessCode:
        code = await self.code_repo.get_by_code(code_str.strip().upper())
        if not code:
            raise ValueError("Invalid code.")
        if code.is_revoked:
            raise ValueError("This code has been revoked by the hospital.")
        if code.is_used:
            raise ValueError("This code has already been used.")
        if code.expires_at and datetime.utcnow() > code.expires_at:
            raise ValueError("This code has expired.")
        return code

    async def revoke_code(self, hospital_user_id: str, code_id: str) -> BystanderAccessCode:
        code = await self.code_repo.get_by_id(code_id)
        if not code or code.hospital_id != hospital_user_id:
            raise ValueError("Code not found.")
        if code.is_used:
            raise ValueError("Cannot revoke a code that has already been used.")
        if code.is_revoked:
            raise ValueError("Code is already revoked.")

        code.is_revoked = True
        code.revoked_at = datetime.utcnow()
        return await self.code_repo.update(code)

    async def get_hospital_code_history(self, hospital_user_id: str) -> list:
        codes = await self.code_repo.list_by_hospital(hospital_user_id)
        results = []
        for c in codes:
            if c.is_revoked:
                status = "revoked"
            elif c.is_used:
                status = "used"
            elif c.expires_at and datetime.utcnow() > c.expires_at:
                status = "expired"
            else:
                status = "active"

            results.append({
                "id": c.id,
                "code": c.code,
                "status": status,
                "patient_name": c.patient_name,
                "blood_group": c.blood_group,
                "used_request_id": c.used_request_id,
                "created_at": c.created_at,
                "expires_at": c.expires_at,
                "revoked_at": c.revoked_at
            })
        return results

    async def create_payment_order(self, code_str: str) -> dict:
        code = await self._get_valid_code(code_str)

        amount = settings.BYSTANDER_REQUEST_FEE_PAISE
        order = await create_razorpay_order(amount_paise=amount, receipt=f"bystander_{code.id}")

        payment = BystanderPayment(
            access_code_id=code.id,
            razorpay_order_id=order["id"],
            amount_paise=amount,
            status="created"
        )
        await self.payment_repo.create(payment)

        return {
            "order_id": order["id"],
            "amount_paise": amount,
            "currency": "INR",
            "razorpay_key_id": settings.RAZORPAY_KEY_ID
        }

    async def verify_and_submit_request(self, dto: BystanderSubmitRequestDTO):
        payment = await self.payment_repo.get_by_order_id(dto.razorpay_order_id)
        # "request_failed" is allowed through so the bystander can retry after a
        # payment that succeeded but whose request could not be created.
        if not payment or payment.status == "paid":
            raise ValueError("Payment order not found or already used.")

        # 1. Validate the code BEFORE touching the payment, so a revoked, expired
        #    or used code never ends up with a payment marked as paid.
        code = await self._get_valid_code(dto.code)
        if code.id != payment.access_code_id:
            raise ValueError("Code does not match this payment.")

        # 2. Verify the Razorpay signature.
        is_valid = verify_razorpay_signature(
            order_id=dto.razorpay_order_id,
            payment_id=dto.razorpay_payment_id,
            signature=dto.razorpay_signature
        )
        if not is_valid:
            payment.status = "failed"
            await self.payment_repo.update(payment)
            raise ValueError("Payment verification failed.")

        # 3. Mark the payment as paid.
        payment.status = "paid"
        payment.razorpay_payment_id = dto.razorpay_payment_id
        payment.paid_at = datetime.utcnow()
        await self.payment_repo.update(payment)

        # 4. Create the blood request and consume the code.
        request_dto = BloodRequestCreateDTO(
            blood_group=dto.blood_group or code.blood_group,
            units_needed=dto.units_needed,
            urgency=dto.urgency,
            note=dto.note or "",
            patient_name=dto.patient_name or code.patient_name,
            patient_age=dto.patient_age,
            patient_condition=dto.patient_condition or "",
            patient_ward=dto.patient_ward or code.patient_ward,
            patient_room=dto.patient_room or code.patient_room,
            patient_bed=dto.patient_bed or "",
            ward_contact_person=dto.ward_contact_person or "",
            ward_contact_phone=dto.ward_contact_phone or "",
            bystander_name=dto.bystander_name,
            bystander_phone=dto.bystander_phone,
            patient_state=dto.patient_state or "",
            patient_district=dto.patient_district or "",
            patient_local_body_type=dto.patient_local_body_type or "",
            patient_local_body_name=dto.patient_local_body_name or "",
            patient_ward_number=dto.patient_ward_number or "",
            search_radius_km=dto.search_radius_km or 50,
            notify_ward_members=False,
            ward_member_message="",
            ward_id=None
        )

        try:
            created_request = await self.donation_use_cases.create_blood_request(code.hospital_id, request_dto)
        except Exception:
            # Money is already captured at this point. Record it so it can be found
            # (and refunded if needed) and let the bystander retry with the same code.
            logger.exception(
                "Bystander request failed after payment: order=%s payment=%s code_id=%s",
                dto.razorpay_order_id, dto.razorpay_payment_id, code.id
            )
            payment.status = "request_failed"
            await self.payment_repo.update(payment)
            raise ValueError(
                "Payment received, but the request could not be created. "
                "Please tap Submit again. You will not be charged twice."
            )

        code.is_used = True
        code.used_request_id = created_request.id
        await self.code_repo.update(code)

        return created_request