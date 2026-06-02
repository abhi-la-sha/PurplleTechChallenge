"""Transaction Pydantic schemas."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import APISchema

STORE_ID_SEPARATOR = "|"


class TransactionCreate(APISchema):
    store_id: str = Field(..., min_length=1, max_length=64)
    transaction_id: str = Field(..., min_length=1, max_length=64)
    timestamp: datetime
    basket_value: Decimal = Field(..., ge=0)


class TransactionRead(APISchema):
    id: uuid.UUID
    store_id: str
    transaction_id: str
    timestamp: datetime
    basket_value: Decimal
    created_at: datetime
    updated_at: datetime


class TransactionListResponse(APISchema):
    items: list[TransactionRead]
    total: int


class TransactionBulkCreateRequest(APISchema):
    transactions: list[TransactionCreate] = Field(..., min_length=1)


class TransactionBulkCreateResponse(APISchema):
    created: int
