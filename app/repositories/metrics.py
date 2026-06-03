from datetime import datetime, timedelta, timezone

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
            select(func.avg(cast(Event.metadata_json["dwell_ms"].astext, Float)))
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
        base = lambda event_type: (
            select(func.count(distinct(Event.visitor_id)))
            .where(Event.store_id == store_id)
            .where(Event.event_type == event_type)
            .where(Event.is_staff.is_(False))
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
        purchase_result = await self._session.execute(
            select(func.count(distinct(Event.visitor_id)))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_JOIN)
            .where(Event.is_staff.is_(False))
            .where(Event.visitor_id.not_in(abandoned_subq))
        )
        return {
            "entry": int(entry_result.scalar_one()),
            "zone_visit": int(zone_result.scalar_one()),
            "billing_queue": int(billing_result.scalar_one()),
            "purchase": int(purchase_result.scalar_one()),
        }


    async def get_zone_visit_counts(self, store_id: str) -> list[tuple[str, int]]:
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

    async def get_zone_avg_dwell_ms(self, store_id: str) -> dict[str, float]:
        zone_col = Event.metadata_json["zone_id"].astext
        dwell_col = cast(Event.metadata_json["dwell_ms"].astext, Float)
        stmt = (
            select(zone_col.label("zone_name"), func.avg(dwell_col).label("avg_dwell"))
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


    async def get_conversion_rates(self, store_id: str) -> dict:
        
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = today_start - timedelta(days=7)

        today_visitors_stmt = (
            select(func.count(distinct(Event.visitor_id)))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.ENTRY)
            .where(Event.is_staff.is_(False))
            .where(Event.timestamp >= today_start)
        )
        today_abandoned_subq = (
            select(Event.visitor_id)
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_ABANDON)
            .where(Event.is_staff.is_(False))
            .where(Event.timestamp >= today_start)
        )
        today_converted_stmt = (
            select(func.count(distinct(Event.visitor_id)))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_JOIN)
            .where(Event.is_staff.is_(False))
            .where(Event.timestamp >= today_start)
            .where(Event.visitor_id.not_in(today_abandoned_subq))
        )

        hist_visitors_stmt = (
            select(func.count(distinct(Event.visitor_id)))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.ENTRY)
            .where(Event.is_staff.is_(False))
            .where(Event.timestamp >= seven_days_ago)
            .where(Event.timestamp < today_start)
        )
        hist_abandoned_subq = (
            select(Event.visitor_id)
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_ABANDON)
            .where(Event.is_staff.is_(False))
            .where(Event.timestamp >= seven_days_ago)
            .where(Event.timestamp < today_start)
        )
        hist_converted_stmt = (
            select(func.count(distinct(Event.visitor_id)))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.BILLING_QUEUE_JOIN)
            .where(Event.is_staff.is_(False))
            .where(Event.timestamp >= seven_days_ago)
            .where(Event.timestamp < today_start)
            .where(Event.visitor_id.not_in(hist_abandoned_subq))
        )

        today_v = int((await self._session.execute(today_visitors_stmt)).scalar_one())
        today_c = int((await self._session.execute(today_converted_stmt)).scalar_one())
        hist_v = int((await self._session.execute(hist_visitors_stmt)).scalar_one())
        hist_c = int((await self._session.execute(hist_converted_stmt)).scalar_one())

        return {
            "today_visitors": today_v,
            "today_rate": round((today_c / today_v * 100), 2) if today_v > 0 else 0.0,
            "historical_visitors": hist_v,
            "historical_rate": round((hist_c / hist_v * 100), 2) if hist_v > 0 else 0.0,
        }

    async def get_dead_zones(
        self, store_id: str, lookback_minutes: int = 30
    ) -> list[str]:
        
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(minutes=lookback_minutes)
        store_active_since = now - timedelta(hours=1)

        activity_check = await self._session.execute(
            select(func.count(Event.id))
            .where(Event.store_id == store_id)
            .where(Event.timestamp >= store_active_since)
            .where(Event.is_staff.is_(False))
        )
        if int(activity_check.scalar_one()) == 0:
            return []

        zone_col = Event.metadata_json["zone_id"].astext

        recently_active_result = await self._session.execute(
            select(distinct(zone_col))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.ZONE_ENTER)
            .where(Event.is_staff.is_(False))
            .where(Event.timestamp >= store_active_since)
            .where(Event.metadata_json.isnot(None))
            .where(zone_col.isnot(None))
        )
        recently_active = {row[0] for row in recently_active_result.fetchall()}

        if not recently_active:
            return []

        still_active_result = await self._session.execute(
            select(distinct(zone_col))
            .where(Event.store_id == store_id)
            .where(Event.event_type == EventType.ZONE_ENTER)
            .where(Event.is_staff.is_(False))
            .where(Event.timestamp >= threshold)
            .where(Event.metadata_json.isnot(None))
            .where(zone_col.isnot(None))
        )
        still_active = {row[0] for row in still_active_result.fetchall()}

        return sorted(recently_active - still_active)