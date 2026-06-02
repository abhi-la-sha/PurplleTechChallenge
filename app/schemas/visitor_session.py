
import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import APISchema


class VisitorSessionBase(APISchema):
    visitor_id: str = Field(..., min_length=1, max_length=64)
    entry_time: datetime
    exit_time: datetime | None = None
    session_duration_seconds: int | None = Field(default=None, ge=0)
    converted: bool = False


class VisitorSessionCreate(VisitorSessionBase):
    pass


class VisitorSessionRead(VisitorSessionBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
