"""Health check route."""

from fastapi import APIRouter

from app.api.deps import HealthServiceDep
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(service: HealthServiceDep) -> HealthResponse:
    return await service.get_health()
