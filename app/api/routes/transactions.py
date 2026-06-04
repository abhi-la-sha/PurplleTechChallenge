
from datetime import datetime

from fastapi import APIRouter, Query, status

from app.api.deps import TransactionServiceDep
from app.schemas.transaction import (
    TransactionBulkCreateRequest,
    TransactionBulkCreateResponse,
    TransactionCreate,
    TransactionListResponse,
    TransactionRead,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreate,
    service: TransactionServiceDep,
) -> TransactionRead:
    return await service.create_transaction(payload)


@router.post("/bulk", response_model=TransactionBulkCreateResponse)
async def create_transactions_bulk(
    payload: TransactionBulkCreateRequest,
    service: TransactionServiceDep,
) -> TransactionBulkCreateResponse:
    return await service.create_bulk(payload)


@router.get("/{transaction_id}", response_model=TransactionRead)
async def get_transaction(
    transaction_id: str,
    service: TransactionServiceDep,
) -> TransactionRead:
    return await service.get_transaction(transaction_id)


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    service: TransactionServiceDep,
    store_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> TransactionListResponse:
    return await service.list_transactions(
        store_id=store_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )
