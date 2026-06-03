from sqlalchemy import distinct, func, select

from app.models.enums import EventType
from app.models.event import Event
from app.models.transaction import Transaction
from app.models.visitor_session import VisitorSession
from app.repositories.base import BaseRepository
from app.schemas.transaction import STORE_ID_SEPARATOR


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


    async def get_store_unique_visitors(self, store_id: str) -> int:
        
        stmt = (
            select(func.count(distinct(Event.visitor_id)))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.ENTRY)
            .where(Event.is_staff.is_(False))
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def get_store_converted_visitors(self, store_id: str) -> int:
        
        # Count unique visitor_ids that appear in BILLING_QUEUE_JOIN
        # but NOT in BILLING_QUEUE_ABANDON for the same store
        joined_sub = (
            select(distinct(Event.visitor_id))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_JOIN)
            .where(Event.is_staff.is_(False))
        ).scalar_subquery()

        abandoned_sub = (
            select(distinct(Event.visitor_id))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_ABANDON)
            .where(Event.is_staff.is_(False))
        ).scalar_subquery()

        # converted = reached billing AND did NOT abandon
        stmt = (
            select(func.count(distinct(Event.visitor_id)))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_JOIN)
            .where(Event.is_staff.is_(False))
            .where(Event.visitor_id.not_in(abandoned_sub))
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def get_store_average_dwell_ms(self, store_id: str) -> float | None:
        
        stmt = (
            select(func.avg(Event.metadata_json["dwell_ms"].as_float()))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.ZONE_DWELL)
            .where(Event.is_staff.is_(False))
            .where(Event.metadata_json["dwell_ms"].as_float().is_not(None))
        )
        result = await self._session.execute(stmt)
        value = result.scalar_one()
        return float(value) if value is not None else None

    async def get_store_queue_depth(self, store_id: str) -> int:
        
        join_stmt = (
            select(func.count(Event.id))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_JOIN)
            .where(Event.is_staff.is_(False))
        )
        abandon_stmt = (
            select(func.count(Event.id))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_ABANDON)
            .where(Event.is_staff.is_(False))
        )
        join_result = await self._session.execute(join_stmt)
        abandon_result = await self._session.execute(abandon_stmt)
        joined = int(join_result.scalar_one())
        abandoned = int(abandon_result.scalar_one())
        return max(0, joined - abandoned)

    async def get_store_abandonment_counts(
        self, store_id: str
    ) -> tuple[int, int]:
        
        join_stmt = (
            select(func.count(Event.id))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_JOIN)
            .where(Event.is_staff.is_(False))
        )
        abandon_stmt = (
            select(func.count(Event.id))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_ABANDON)
            .where(Event.is_staff.is_(False))
        )
        join_result = await self._session.execute(join_stmt)
        abandon_result = await self._session.execute(abandon_stmt)
        return int(abandon_result.scalar_one()), int(join_result.scalar_one())

    async def get_store_average_basket_value(self, store_id: str) -> float | None:
        
        prefix = f"{store_id}{STORE_ID_SEPARATOR}%"
        stmt = select(func.avg(Transaction.basket_value)).where(
            Transaction.transaction_id.like(prefix)
        )
        result = await self._session.execute(stmt)
        value = result.scalar_one()
        return float(value) if value is not None else None