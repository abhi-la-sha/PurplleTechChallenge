
import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.models.enums import EventType
from app.schemas.common import APISchema


class EventBase(APISchema):
    visitor_id: str = Field(..., min_length=1, max_length=64)
    camera_id: uuid.UUID | None = None
    zone_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    event_type: EventType
    timestamp: datetime
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata_json: dict[str, Any] | None = None


class EventCreate(EventBase):
    pass


class EventRead(EventBase):
    id: uuid.UUID
    created_at: datetime


class EventListResponse(APISchema):
    items: list[EventRead]
    total: int
    limit: int
    offset: int


class EventBulkCreateRequest(APISchema):
    events: list[EventCreate] = Field(..., min_length=1)


class EventStatsResponse(APISchema):
    total_events: int
