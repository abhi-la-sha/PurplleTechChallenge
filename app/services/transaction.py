"""Transaction ingestion service orchestration."""

from datetime import datetime

from fastapi import HTTPException, status

from app.models.transaction import Transaction
from app.repositories.transaction import TransactionRepository
from app.schemas.transaction import (
    STORE_ID_SEPARATOR,
    TransactionBulkCreateRequest,
    TransactionBulkCreateResponse,
    TransactionCreate,
    TransactionListResponse,
    TransactionRead,
)


class TransactionService:
    """Coordinates transaction validation and persistence."""

    def __init__(self, repository: TransactionRepository) -> None:
        self._repository = repository

    async def create_transaction(self, payload: TransactionCreate) -> TransactionRead:
        stored_id = _encode_stored_transaction_id(payload.store_id, payload.transaction_id)
        if await self._repository.exists(stored_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Transaction with this transaction_id already exists",
            )

        entity = Transaction(
            transaction_id=stored_id,
            transaction_timestamp=payload.timestamp,
            basket_value=payload.basket_value,
        )
        created = await self._repository.create(entity)
        return _to_transaction_read(created)

    async def create_bulk(
        self,
        payload: TransactionBulkCreateRequest,
    ) -> TransactionBulkCreateResponse:
        for item in payload.transactions:
            stored_id = _encode_stored_transaction_id(item.store_id, item.transaction_id)
            if await self._repository.exists(stored_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Transaction with this transaction_id already exists: "
                        f"{item.transaction_id}"
                    ),
                )

        entities = [
            Transaction(
                transaction_id=_encode_stored_transaction_id(
                    item.store_id,
                    item.transaction_id,
                ),
                transaction_timestamp=item.timestamp,
                basket_value=item.basket_value,
            )
            for item in payload.transactions
        ]
        created = await self._repository.create_many(entities)
        return TransactionBulkCreateResponse(created=created)

    async def get_transaction(self, transaction_id: str) -> TransactionRead:
        entity = await self._repository.get_by_transaction_id(transaction_id)
        if entity is None:
            entity = await self._repository.get_by_business_transaction_id(transaction_id)
        if entity is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found",
            )
        return _to_transaction_read(entity)

    async def list_transactions(
        self,
        *,
        store_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> TransactionListResponse:
        rows = await self._repository.list(
            store_id=store_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
        total = await self._repository.count(
            store_id=store_id,
            start_time=start_time,
            end_time=end_time,
        )
        return TransactionListResponse(
            items=[_to_transaction_read(row) for row in rows],
            total=total,
        )


def _encode_stored_transaction_id(store_id: str, transaction_id: str) -> str:
    return f"{store_id}{STORE_ID_SEPARATOR}{transaction_id}"


def _decode_stored_transaction_id(stored_id: str) -> tuple[str, str]:
    if STORE_ID_SEPARATOR in stored_id:
        store_id, business_id = stored_id.split(STORE_ID_SEPARATOR, 1)
        return store_id, business_id
    return "", stored_id


def _to_transaction_read(entity: Transaction) -> TransactionRead:
    store_id, business_id = _decode_stored_transaction_id(entity.transaction_id)
    return TransactionRead(
        id=entity.id,
        store_id=store_id,
        transaction_id=business_id,
        timestamp=entity.transaction_timestamp,
        basket_value=entity.basket_value,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
