
from fastapi import APIRouter

from app.api.deps import StoreMetricsServiceDep
from app.schemas.metrics import StoreMetricsResponse

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("/{store_id}/metrics", response_model=StoreMetricsResponse)
async def get_store_metrics(
    store_id: str,
    service: StoreMetricsServiceDep,
) -> StoreMetricsResponse:
    
    return await service.get_store_metrics(store_id)