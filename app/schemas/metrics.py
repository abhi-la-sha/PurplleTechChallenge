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
    queue_depth: int = Field(..., ge=0)
    abandonment_rate: float = Field(..., ge=0.0, description="Percentage 0–100")
    average_basket_value: float = Field(..., ge=0.0)


class FunnelStage(APISchema):
    stage: str
    count: int = Field(..., ge=0)
    drop_off_from_previous_pct: float = Field(
        ..., ge=0.0, description="% of previous stage that did not reach this stage"
    )


class FunnelResponse(APISchema):
    
    store_id: str
    stages: list[FunnelStage]


class HeatmapZone(APISchema):
    zone_id: str
    visit_count: int = Field(..., ge=0)
    avg_dwell_seconds: float = Field(..., ge=0.0)
    normalised_score: float = Field(..., ge=0.0, le=100.0, description="0–100 relative score")


class HeatmapResponse(APISchema):

    store_id: str
    zones: list[HeatmapZone]
    data_confidence: bool = Field(
        ..., description="False when fewer than 20 unique visitors in window"
    )