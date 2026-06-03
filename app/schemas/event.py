import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.models.enums import EventType
from app.schemas.common import APISchema


# ── existing schemas (unchanged) ─────────────────────────────────────────────

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


# ── new ingest schemas ────────────────────────────────────────────────────────

class IngestEventItem(APISchema):
    """Single event in the pipeline's schema format (matches challenge spec)."""

    event_id: uuid.UUID = Field(..., description="Client-generated UUID — used for idempotency")
    store_id: str = Field(..., min_length=1, max_length=64)
    camera_id: str | None = Field(default=None, description="Camera code string e.g. CAM_ENTRY_01")
    visitor_id: str = Field(..., min_length=1, max_length=64)
    event_type: EventType
    timestamp: datetime
    zone_id: str | None = Field(default=None, description="Zone name string e.g. SKINCARE")
    dwell_ms: int | None = Field(default=None, ge=0)
    is_staff: bool = False
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: dict[str, Any] | None = None


class IngestRequest(APISchema):
    events: list[IngestEventItem] = Field(..., min_length=1, max_length=500)


class IngestErrorItem(APISchema):
    event_id: str
    error: str


class IngestResponse(APISchema):
    ingested: int
    duplicates: int
    errors: list[IngestErrorItem]