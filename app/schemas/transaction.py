
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import APISchema


class TransactionBase(APISchema):
    transaction_id: str = Field(..., min_length=1, max_length=64)
    transaction_timestamp: datetime
    basket_value: Decimal = Field(..., ge=0)
    visitor_session_id: uuid.UUID | None = None


class TransactionCreate(TransactionBase):
    pass


class TransactionRead(TransactionBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
