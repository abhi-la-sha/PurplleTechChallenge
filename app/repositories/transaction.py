
import uuid

from sqlalchemy import select

from app.models.transaction import Transaction
from app.repositories.base import BaseRepository


class TransactionRepository(BaseRepository):
    async def create(self, transaction: Transaction) -> Transaction:
        self._session.add(transaction)
        await self._session.flush()
        await self._session.refresh(transaction)
        return transaction

    async def get_by_id(self, transaction_pk: uuid.UUID) -> Transaction | None:
        return await self._session.get(Transaction, transaction_pk)

    async def get_by_transaction_id(self, transaction_id: str) -> Transaction | None:
        stmt = select(Transaction).where(Transaction.transaction_id == transaction_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Transaction]:
        stmt = select(Transaction).order_by(Transaction.transaction_timestamp.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, transaction: Transaction) -> Transaction:
        await self._session.flush()
        await self._session.refresh(transaction)
        return transaction

    async def delete(self, transaction_pk: uuid.UUID) -> bool:
        transaction = await self.get_by_id(transaction_pk)
        if transaction is None:
            return False
        await self._session.delete(transaction)
        await self._session.flush()
        return True
