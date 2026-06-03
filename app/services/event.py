
import logging
import uuid
from typing import Any

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
    IngestErrorItem,
    IngestRequest,
    IngestResponse,
)

logger = logging.getLogger(__name__)


class EventService:


    def __init__(self, repository: EventRepository) -> None:
        self._repository = repository

    async def create_event(self, payload: EventCreate) -> EventRead:
        event = Event(**payload.model_dump())
        created = await self._repository.create(event)
        return EventRead.model_validate(created)

    async def create_bulk(self, payload: EventBulkCreateRequest) -> int:
        entities = [Event(**item.model_dump()) for item in payload.events]
        return await self._repository.create_many(entities)

    async def ingest_batch(self, payload: IngestRequest) -> IngestResponse:
        
        all_ids = [item.event_id for item in payload.events]
        existing_ids = await self._repository.get_existing_ids(all_ids)

        new_events: list[Event] = []
        errors: list[IngestErrorItem] = []
        duplicate_count = 0

        for item in payload.events:
            if item.event_id in existing_ids:
                duplicate_count += 1
                continue
            try:
                metadata: dict[str, Any] = {
                    "camera_id": item.camera_id,
                    "zone_id": item.zone_id,
                    "dwell_ms": item.dwell_ms,
                }
                if item.metadata:
                    metadata.update(item.metadata)

                event = Event(
                    id=item.event_id,          # use client-provided UUID as PK
                    store_id=item.store_id,
                    visitor_id=item.visitor_id,
                    event_type=item.event_type,
                    timestamp=item.timestamp,
                    is_staff=item.is_staff,
                    confidence=item.confidence,
                    metadata_json=metadata,
                    # camera_id / zone_id UUID FKs left null —
                    # raw string identifiers are in metadata_json
                    camera_id=None,
                    zone_id=None,
                    session_id=None,
                )
                new_events.append(event)
            except Exception as exc:
                logger.warning(
                    "ingest_item_error",
                    extra={"event_id": str(item.event_id), "error": str(exc)},
                )
                errors.append(
                    IngestErrorItem(event_id=str(item.event_id), error=str(exc))
                )

        ingested = await self._repository.create_many(new_events)
        return IngestResponse(
            ingested=ingested,
            duplicates=duplicate_count,
            errors=errors,
        )

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