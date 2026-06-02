
import uuid
from datetime import datetime

from sqlalchemy import select

from app.models.enums import EventType
from app.models.event import Event
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository):
    async def create(self, event: Event) -> Event:
        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)
        return event

    async def get_by_id(self, event_id: uuid.UUID) -> Event | None:
        return await self._session.get(Event, event_id)

    async def list_by_visitor(
        self,
        visitor_id: str,
        *,
        limit: int = 100,
    ) -> list[Event]:
        stmt = (
            select(Event)
            .where(Event.visitor_id == visitor_id)
            .order_by(Event.timestamp.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_session(self, session_id: uuid.UUID) -> list[Event]:
        stmt = (
            select(Event)
            .where(Event.session_id == session_id)
            .order_by(Event.timestamp.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_type_and_range(
        self,
        event_type: EventType,
        start: datetime,
        end: datetime,
    ) -> list[Event]:
        stmt = (
            select(Event)
            .where(
                Event.event_type == event_type,
                Event.timestamp >= start,
                Event.timestamp <= end,
            )
            .order_by(Event.timestamp.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, event_id: uuid.UUID) -> bool:
        event = await self.get_by_id(event_id)
        if event is None:
            return False
        await self._session.delete(event)
        await self._session.flush()
        return True
