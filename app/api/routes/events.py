
from fastapi import APIRouter

from app.api.deps import PlaceholderServiceDep

router = APIRouter(prefix="/events", tags=["events"])


@router.api_route("", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def events_not_implemented(service: PlaceholderServiceDep) -> None:
    await service.not_implemented()
