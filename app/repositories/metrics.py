
from sqlalchemy import func, select

from app.models.transaction import Transaction
from app.models.visitor_session import VisitorSession
from app.repositories.base import BaseRepository


class MetricsRepository(BaseRepository):
    

    async def get_total_visitors(self) -> int:
        stmt = select(func.count(VisitorSession.id))
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def get_converted_visitors(self) -> int:
        stmt = select(func.count(VisitorSession.id)).where(
            VisitorSession.converted.is_(True)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def get_average_dwell_time(self) -> float | None:
        stmt = select(func.avg(VisitorSession.session_duration_seconds)).where(
            VisitorSession.session_duration_seconds.is_not(None)
        )
        result = await self._session.execute(stmt)
        value = result.scalar_one()
        return float(value) if value is not None else None

    async def get_average_basket_value(self) -> float | None:
        stmt = select(func.avg(Transaction.basket_value))
        result = await self._session.execute(stmt)
        value = result.scalar_one()
        return float(value) if value is not None else None
