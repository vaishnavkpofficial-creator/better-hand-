from fastapi import APIRouter, Depends, HTTPException, status
from app.domain.entities.user import User
from app.application.dto.bystander_dto import (
    BystanderCodeCreateDTO, BystanderCodeResponse,
    BystanderOrderRequestDTO, BystanderOrderResponse,
    BystanderSubmitRequestDTO
)
from app.application.use_cases.bystander_use_cases import BystanderUseCases
from app.dependencies.db_repos import get_bystander_use_cases
from app.dependencies.auth import require_hospital

router = APIRouter()


# ─── Hospital side (authenticated) ───

@router.post("/generate-code/", response_model=BystanderCodeResponse, status_code=status.HTTP_201_CREATED)
async def generate_code(
    dto: BystanderCodeCreateDTO,
    current_user: User = Depends(require_hospital),
    use_cases: BystanderUseCases = Depends(get_bystander_use_cases)
):
    try:
        code = await use_cases.generate_code(current_user.id, dto)
        return BystanderCodeResponse(id=code.id, code=code.code, expires_at=code.expires_at)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ─── Bystander side (public — no login) ───

@router.post("/create-order/", response_model=BystanderOrderResponse)
async def create_order(
    dto: BystanderOrderRequestDTO,
    use_cases: BystanderUseCases = Depends(get_bystander_use_cases)
):
    try:
        order = await use_cases.create_payment_order(dto.code)
        return BystanderOrderResponse(**order)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/requests/", status_code=status.HTTP_201_CREATED)
async def submit_bystander_request(
    dto: BystanderSubmitRequestDTO,
    use_cases: BystanderUseCases = Depends(get_bystander_use_cases)
):
    try:
        br = await use_cases.verify_and_submit_request(dto)
        return {
            "id": br.id,
            "blood_group": br.blood_group,
            "status": br.status,
            "message": "Blood request submitted successfully."
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/codes/")
async def get_code_history(
    current_user: User = Depends(require_hospital),
    use_cases: BystanderUseCases = Depends(get_bystander_use_cases)
):
    return await use_cases.get_hospital_code_history(current_user.id)


@router.post("/codes/{code_id}/revoke/")
async def revoke_code(
    code_id: str,
    current_user: User = Depends(require_hospital),
    use_cases: BystanderUseCases = Depends(get_bystander_use_cases)
):
    try:
        code = await use_cases.revoke_code(current_user.id, code_id)
        return {"message": "Code revoked.", "id": code.id, "code": code.code}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))