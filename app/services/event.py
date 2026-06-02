"""Event ingestion service orchestration."""

import uuid

from fastapi import HTTPException, status

from app.models.event import Event
from app.models.enums import EventType
from app.repositories.event import EventRepository
from app.schemas.event import (
    EventBulkCreateRequest,
    EventCreate,
    EventListResponse,
    EventRead,
    EventStatsResponse,
)


class EventService:
    """Coordinates event validation and persistence."""

    def __init__(self, repository: EventRepository) -> None:
        self._repository = repository

    async def create_event(self, payload: EventCreate) -> EventRead:
        event = Event(**payload.model_dump())
        created = await self._repository.create(event)
        return EventRead.model_validate(created)

    async def create_bulk(self, payload: EventBulkCreateRequest) -> int:
        entities = [Event(**item.model_dump()) for item in payload.events]
        return await self._repository.create_many(entities)

    async def get_event(self, event_id: uuid.UUID) -> EventRead:
        event = await self._repository.get_by_id(event_id)
        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )
        return EventRead.model_validate(event)

    async def list_events(
        self,
        *,
        visitor_id: str | None = None,
        event_type: EventType | None = None,
        camera_id: uuid.UUID | None = None,
        zone_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> EventListResponse:
        events = await self._repository.list(
            visitor_id=visitor_id,
            event_type=event_type,
            camera_id=camera_id,
            zone_id=zone_id,
            session_id=session_id,
            limit=limit,
            offset=offset,
        )
        total = await self._repository.count(
            visitor_id=visitor_id,
            event_type=event_type,
            camera_id=camera_id,
            zone_id=zone_id,
            session_id=session_id,
        )
        return EventListResponse(
            items=[EventRead.model_validate(event) for event in events],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_stats(self) -> EventStatsResponse:
        total = await self._repository.count()
        return EventStatsResponse(total_events=total)
