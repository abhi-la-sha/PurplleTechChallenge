from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select

from app.models.enums import EventType
from app.models.event import Event
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository):
    async def create(self, event: Event) -> Event:
        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)
        return event

    async def create_many(self, events: list[Event]) -> int:
        if not events:
            return 0
        self._session.add_all(events)
        await self._session.flush()
        return len(events)

    async def get_by_id(self, event_id: uuid.UUID) -> Event | None:
        return await self._session.get(Event, event_id)

    async def get_existing_ids(self, event_ids: list[uuid.UUID]) -> set[uuid.UUID]:
        """Return the subset of event_ids that already exist in the database."""
        if not event_ids:
            return set()
        stmt = select(Event.id).where(Event.id.in_(event_ids))
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def list(
        self,
        *,
        visitor_id: str | None = None,
        event_type: EventType | None = None,
        camera_id: uuid.UUID | None = None,
        zone_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Event]:
        stmt = self._filtered_query(
            visitor_id=visitor_id,
            event_type=event_type,
            camera_id=camera_id,
            zone_id=zone_id,
            session_id=session_id,
        ).order_by(Event.timestamp.desc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count(
        self,
        *,
        visitor_id: str | None = None,
        event_type: EventType | None = None,
        camera_id: uuid.UUID | None = None,
        zone_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
    ) -> int:
        stmt = self._filtered_query(
            visitor_id=visitor_id,
            event_type=event_type,
            camera_id=camera_id,
            zone_id=zone_id,
            session_id=session_id,
        ).with_only_columns(func.count(Event.id))
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def list_by_session(self, session_id: uuid.UUID) -> list[Event]:
        stmt = (
            select(Event)
            .where(Event.session_id == session_id)
            .order_by(Event.timestamp.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def exists(self, event_id: uuid.UUID) -> bool:
        stmt = select(func.count(Event.id)).where(Event.id == event_id)
        result = await self._session.execute(stmt)
        return int(result.scalar_one()) > 0

    def _filtered_query(
        self,
        *,
        visitor_id: str | None = None,
        event_type: EventType | None = None,
        camera_id: uuid.UUID | None = None,
        zone_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
    ) -> Select[tuple[Event]]:
        stmt: Select[tuple[Event]] = select(Event)
        if visitor_id is not None:
            stmt = stmt.where(Event.visitor_id == visitor_id)
        if event_type is not None:
            stmt = stmt.where(Event.event_type == event_type)
        if camera_id is not None:
            stmt = stmt.where(Event.camera_id == camera_id)
        if zone_id is not None:
            stmt = stmt.where(Event.zone_id == zone_id)
        if session_id is not None:
            stmt = stmt.where(Event.session_id == session_id)
        return stmt

    async def delete(self, event_id: uuid.UUID) -> bool:
        event = await self.get_by_id(event_id)
        if event is None:
            return False
        await self._session.delete(event)
        await self._session.flush()
        return True