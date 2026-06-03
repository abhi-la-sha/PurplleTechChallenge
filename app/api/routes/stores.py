
from fastapi import APIRouter

from app.api.deps import StoreMetricsServiceDep
from app.schemas.metrics import (
    AnomaliesResponse,
    FunnelResponse,
    HeatmapResponse,
    StoreMetricsResponse,
)

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("/{store_id}/metrics", response_model=StoreMetricsResponse)
async def get_store_metrics(
    store_id: str,
    service: StoreMetricsServiceDep,
) -> StoreMetricsResponse:
    
    return await service.get_store_metrics(store_id)


@router.get("/{store_id}/funnel", response_model=FunnelResponse)
async def get_store_funnel(
    store_id: str,
    service: StoreMetricsServiceDep,
) -> FunnelResponse:
    
    return await service.get_store_funnel(store_id)


@router.get("/{store_id}/heatmap", response_model=HeatmapResponse)
async def get_store_heatmap(
    store_id: str,
    service: StoreMetricsServiceDep,
) -> HeatmapResponse:
    
    return await service.get_store_heatmap(store_id)


@router.get("/{store_id}/anomalies", response_model=AnomaliesResponse)
async def get_store_anomalies(
    store_id: str,
    service: StoreMetricsServiceDep,
) -> AnomaliesResponse:
    return await service.get_store_anomalies(store_id)