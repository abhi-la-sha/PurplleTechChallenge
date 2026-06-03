
from typing import Literal
from app.schemas.common import APISchema
from datetime import datetime


class StoreHealth(APISchema):
    store_id: str
    last_event_timestamp: datetime
    feed_status: Literal["OK", "STALE_FEED"]


class HealthResponse(APISchema):
    status: Literal["healthy"] = "healthy"
    stores: list[StoreHealth] = []