import uuid

from fastapi import APIRouter, Query, status

from app.api.deps import EventServiceDep
from app.models.enums import EventType
from app.schemas.event import (
    EventBulkCreateRequest,
    EventCreate,
    EventListResponse,
    EventRead,
    EventStatsResponse,
    IngestRequest,
    IngestResponse,
)

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_200_OK)
async def ingest_events(
    payload: IngestRequest,
    service: EventServiceDep,
) -> IngestResponse:

    return await service.ingest_batch(payload)


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(payload: EventCreate, service: EventServiceDep) -> EventRead:
    return await service.create_event(payload)


@router.post("/bulk")
async def create_events_bulk(
    payload: EventBulkCreateRequest,
    service: EventServiceDep,
) -> dict[str, int]:
    created_count = await service.create_bulk(payload)
    return {"created_count": created_count}


@router.get("/stats", response_model=EventStatsResponse)
async def get_event_stats(service: EventServiceDep) -> EventStatsResponse:
    return await service.get_stats()


@router.get("/{event_id}", response_model=EventRead)
async def get_event(event_id: uuid.UUID, service: EventServiceDep) -> EventRead:
    return await service.get_event(event_id)


@router.get("", response_model=EventListResponse)
async def list_events(
    service: EventServiceDep,
    visitor_id: str | None = None,
    event_type: EventType | None = None,
    camera_id: uuid.UUID | None = None,
    zone_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> EventListResponse:
    return await service.list_events(
        visitor_id=visitor_id,
        event_type=event_type,
        camera_id=camera_id,
        zone_id=zone_id,
        session_id=session_id,
        limit=limit,
        offset=offset,
    )