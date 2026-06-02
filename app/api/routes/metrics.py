
from fastapi import APIRouter

from app.api.deps import MetricsServiceDep
from app.schemas.metrics import MetricsResponse

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=MetricsResponse)
async def get_metrics(service: MetricsServiceDep) -> MetricsResponse:
    return await service.get_metrics()
