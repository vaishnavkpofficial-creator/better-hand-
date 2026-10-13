from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.bystander import BystanderAccessCode, BystanderPayment

class BystanderAccessCodeRepository(ABC):
    @abstractmethod
    async def create(self, code: BystanderAccessCode) -> BystanderAccessCode:
        pass

    @abstractmethod
    async def get_by_code(self, code: str) -> Optional[BystanderAccessCode]:
        pass

    @abstractmethod
    async def get_by_id(self, code_id: str) -> Optional[BystanderAccessCode]:
        pass

    @abstractmethod
    async def update(self, code: BystanderAccessCode) -> BystanderAccessCode:
        pass

    @abstractmethod
    async def list_by_hospital(self, hospital_id: str) -> List[BystanderAccessCode]:
        pass


class BystanderPaymentRepository(ABC):
    @abstractmethod
    async def create(self, payment: BystanderPayment) -> BystanderPayment:
        pass

    @abstractmethod
    async def get_by_order_id(self, razorpay_order_id: str) -> Optional[BystanderPayment]:
        pass

    @abstractmethod
    async def update(self, payment: BystanderPayment) -> BystanderPayment:
        pass