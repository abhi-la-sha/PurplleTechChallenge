
from fastapi import APIRouter

from app.api.deps import PlaceholderServiceDep

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.api_route("", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def metrics_not_implemented(service: PlaceholderServiceDep) -> None:
    await service.not_implemented()
