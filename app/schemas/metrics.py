from pydantic import Field

from app.schemas.common import APISchema


class MetricsResponse(APISchema):
    
    total_visitors: int = Field(..., ge=0)
    converted_visitors: int = Field(..., ge=0)
    conversion_rate: float = Field(..., ge=0.0)
    average_dwell_time_seconds: float = Field(..., ge=0.0)
    average_basket_value: float = Field(..., ge=0.0)


class StoreMetricsResponse(APISchema):
    
    store_id: str
    unique_visitors: int = Field(..., ge=0)
    converted_visitors: int = Field(..., ge=0)
    conversion_rate: float = Field(..., ge=0.0, description="Percentage 0–100")
    average_dwell_time_seconds: float = Field(..., ge=0.0)
    queue_depth: int = Field(..., ge=0, description="Current billing queue depth")
    abandonment_rate: float = Field(..., ge=0.0, description="Percentage 0–100")
    average_basket_value: float = Field(..., ge=0.0)