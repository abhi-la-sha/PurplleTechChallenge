
import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import APISchema


class ZoneBase(APISchema):
    camera_id: uuid.UUID
    zone_name: str = Field(..., min_length=1, max_length=128)
    zone_type: str = Field(..., min_length=1, max_length=64)
    polygon_json: dict[str, Any] = Field(
        ...,
        description="Arbitrary polygon definition (points, labels, etc.)",
    )


class ZoneCreate(ZoneBase):
    pass


class ZoneRead(ZoneBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
