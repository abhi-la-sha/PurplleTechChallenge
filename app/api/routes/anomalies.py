
from fastapi import APIRouter

from app.api.deps import PlaceholderServiceDep

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.api_route("", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def anomalies_not_implemented(service: PlaceholderServiceDep) -> None:
    await service.not_implemented()
