
import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import APISchema


class CameraBase(APISchema):
    camera_name: str = Field(..., min_length=1, max_length=128)
    camera_code: str = Field(..., min_length=1, max_length=32)
    purpose: str | None = None
    is_active: bool = True


class CameraCreate(CameraBase):
    pass


class CameraRead(CameraBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
