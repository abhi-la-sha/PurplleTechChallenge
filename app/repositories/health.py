from datetime import datetime
from sqlalchemy import text
from sqlalchemy import func, select
from app.models.event import Event
from app.repositories.base import BaseRepository


class HealthRepository(BaseRepository):
    """Repository for health-related infrastructure checks."""

    async def ping_database(self) -> bool:
        """Verify database connectivity."""
        result = await self._session.execute(text("SELECT 1"))
        return result.scalar_one() == 1
    async def get_last_event_per_store(self) -> list[tuple[str, datetime]]:
        stmt = (
        select(
            Event.store_id,
            func.max(Event.timestamp).label("last_event_timestamp"),
        )
        .group_by(Event.store_id))
        result = await self._session.execute(stmt)
        return [(row.store_id, row.last_event_timestamp) for row in result.all()]