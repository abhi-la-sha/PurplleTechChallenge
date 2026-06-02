
from typing import Literal

from app.schemas.common import APISchema


class HealthResponse(APISchema):
    status: Literal["healthy"] = "healthy"
