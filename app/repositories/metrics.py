from sqlalchemy import Float, cast, distinct, func, select

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
        abandoned_subq = (
            select(Event.visitor_id)
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_ABANDON)
            .where(Event.is_staff.is_(False))
        )
        stmt = (
            select(func.count(distinct(Event.visitor_id)))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_JOIN)
            .where(Event.is_staff.is_(False))
            .where(Event.visitor_id.not_in(abandoned_subq))
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def get_store_average_dwell_ms(self, store_id: str) -> float | None:
        stmt = (
            select(
                func.avg(cast(Event.metadata_json["dwell_ms"].astext, Float))
            )
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.ZONE_DWELL)
            .where(Event.is_staff.is_(False))
            .where(Event.metadata_json["dwell_ms"].astext.isnot(None))
        )
        result = await self._session.execute(stmt)
        value = result.scalar_one()
        return float(value) if value is not None else None

    async def get_store_queue_depth(self, store_id: str) -> int:
        join_result = await self._session.execute(
            select(func.count(Event.id))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_JOIN)
            .where(Event.is_staff.is_(False))
        )
        abandon_result = await self._session.execute(
            select(func.count(Event.id))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_ABANDON)
            .where(Event.is_staff.is_(False))
        )
        return max(0, int(join_result.scalar_one()) - int(abandon_result.scalar_one()))

    async def get_store_abandonment_counts(self, store_id: str) -> tuple[int, int]:
        join_result = await self._session.execute(
            select(func.count(Event.id))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_JOIN)
            .where(Event.is_staff.is_(False))
        )
        abandon_result = await self._session.execute(
            select(func.count(Event.id))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_ABANDON)
            .where(Event.is_staff.is_(False))
        )
        return int(abandon_result.scalar_one()), int(join_result.scalar_one())

    async def get_store_average_basket_value(self, store_id: str) -> float | None:
        prefix = f"{store_id}{STORE_ID_SEPARATOR}%"
        stmt = select(func.avg(Transaction.basket_value)).where(
            Transaction.transaction_id.like(prefix)
        )
        result = await self._session.execute(stmt)
        value = result.scalar_one()
        return float(value) if value is not None else None


    async def get_funnel_stage_counts(self, store_id: str) -> dict[str, int]:

        base = (
            lambda event_type: (
                select(func.count(distinct(Event.visitor_id)))
                .where(Event.store_id == store_id)
                .where(Event.event_type == event_type)
                .where(Event.is_staff.is_(False))
            )
        )

        entry_result = await self._session.execute(base(EventType.ENTRY))
        zone_result = await self._session.execute(base(EventType.ZONE_ENTER))
        billing_result = await self._session.execute(base(EventType.BILLING_QUEUE_JOIN))

        abandoned_subq = (
            select(Event.visitor_id)
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_ABANDON)
            .where(Event.is_staff.is_(False))
        )
        purchase_stmt = (
            select(func.count(distinct(Event.visitor_id)))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_JOIN)
            .where(Event.is_staff.is_(False))
            .where(Event.visitor_id.not_in(abandoned_subq))
        )
        purchase_result = await self._session.execute(purchase_stmt)

        return {
            "entry": int(entry_result.scalar_one()),
            "zone_visit": int(zone_result.scalar_one()),
            "billing_queue": int(billing_result.scalar_one()),
            "purchase": int(purchase_result.scalar_one()),
        }


    async def get_zone_visit_counts(
        self, store_id: str
    ) -> list[tuple[str, int]]:
        zone_col = Event.metadata_json["zone_id"].astext
        stmt = (
            select(zone_col.label("zone_name"), func.count(Event.id).label("cnt"))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.ZONE_ENTER)
            .where(Event.is_staff.is_(False))
            .where(Event.metadata_json.isnot(None))
            .where(zone_col.isnot(None))
            .group_by(zone_col)
            .order_by(func.count(Event.id).desc())
        )
        result = await self._session.execute(stmt)
        return [(row.zone_name, row.cnt) for row in result.fetchall()]

    async def get_zone_avg_dwell_ms(
        self, store_id: str
    ) -> dict[str, float]:
    
        zone_col = Event.metadata_json["zone_id"].astext
        dwell_col = cast(Event.metadata_json["dwell_ms"].astext, Float)
        stmt = (
            select(
                zone_col.label("zone_name"),
                func.avg(dwell_col).label("avg_dwell"),
            )
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.ZONE_DWELL)
            .where(Event.is_staff.is_(False))
            .where(Event.metadata_json.isnot(None))
            .where(zone_col.isnot(None))
            .where(Event.metadata_json["dwell_ms"].astext.isnot(None))
            .group_by(zone_col)
        )
        result = await self._session.execute(stmt)
        return {
            row.zone_name: float(row.avg_dwell)
            for row in result.fetchall()
            if row.avg_dwell is not None
        }

    async def get_store_unique_visitor_count(self, store_id: str) -> int:

        stmt = (
            select(func.count(distinct(Event.visitor_id)))
            .where(Event.store_id == store_id)
            .where(Event.is_staff.is_(False))
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())