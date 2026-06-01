"""Root metadata route."""

from fastapi import APIRouter

from app.api.deps import RootServiceDep
from app.schemas.root import RootResponse

router = APIRouter(tags=["root"])


@router.get("/", response_model=RootResponse)
async def root(service: RootServiceDep) -> RootResponse:
    return service.get_root()
