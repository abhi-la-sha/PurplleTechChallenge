from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Select, func, or_, select

from app.models.transaction import Transaction
from app.repositories.base import BaseRepository
from app.schemas.transaction import STORE_ID_SEPARATOR


class TransactionRepository(BaseRepository):
    async def create(self, transaction: Transaction) -> Transaction:
        self._session.add(transaction)
        await self._session.flush()
        await self._session.refresh(transaction)
        return transaction

    async def create_many(self, transactions: list[Transaction]) -> int:
        if not transactions:
            return 0
        self._session.add_all(transactions)
        await self._session.flush()
        return len(transactions)

    async def get_by_id(self, transaction_pk: uuid.UUID) -> Transaction | None:
        return await self._session.get(Transaction, transaction_pk)

    async def get_by_transaction_id(self, transaction_id: str) -> Transaction | None:
        stmt = select(Transaction).where(Transaction.transaction_id == transaction_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_business_transaction_id(
        self,
        business_transaction_id: str,
    ) -> Transaction | None:
        suffix = f"{STORE_ID_SEPARATOR}{business_transaction_id}"
        stmt = select(Transaction).where(
            or_(
                Transaction.transaction_id == business_transaction_id,
                Transaction.transaction_id.like(f"%{suffix}"),
            )
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        if not rows:
            return None
        if len(rows) == 1:
            return rows[0]
        exact_suffix = [row for row in rows if row.transaction_id.endswith(suffix)]
        return exact_suffix[0] if exact_suffix else rows[0]

    async def exists(self, transaction_id: str) -> bool:
        stmt = (
            select(func.count(Transaction.id))
            .where(Transaction.transaction_id == transaction_id)
            .with_only_columns(func.count(Transaction.id))
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one()) > 0

    async def list(
        self,
        *,
        store_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Transaction]:
        stmt = self._filtered_query(
            store_id=store_id,
            start_time=start_time,
            end_time=end_time,
        ).order_by(Transaction.transaction_timestamp.desc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count(
        self,
        *,
        store_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        stmt = self._filtered_query(
            store_id=store_id,
            start_time=start_time,
            end_time=end_time,
        ).with_only_columns(func.count(Transaction.id))
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    def _filtered_query(
        self,
        *,
        store_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Select[tuple[Transaction]]:
        stmt: Select[tuple[Transaction]] = select(Transaction)
        if store_id is not None:
            prefix = f"{store_id}{STORE_ID_SEPARATOR}%"
            stmt = stmt.where(Transaction.transaction_id.like(prefix))
        if start_time is not None:
            stmt = stmt.where(Transaction.transaction_timestamp >= start_time)
        if end_time is not None:
            stmt = stmt.where(Transaction.transaction_timestamp <= end_time)
        return stmt

    async def delete(self, transaction_pk: uuid.UUID) -> bool:
        transaction = await self.get_by_id(transaction_pk)
        if transaction is None:
            return False
        await self._session.delete(transaction)
        await self._session.flush()
        return True
