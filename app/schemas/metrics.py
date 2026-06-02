
from pydantic import Field

from app.schemas.common import APISchema


class MetricsResponse(APISchema):
    total_visitors: int = Field(..., ge=0)
    converted_visitors: int = Field(..., ge=0)
    conversion_rate: float = Field(..., ge=0.0)
    average_dwell_time_seconds: float = Field(..., ge=0.0)
    average_basket_value: float = Field(..., ge=0.0)
