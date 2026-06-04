from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def dashboard() -> FileResponse:
    return FileResponse("app/dashboard/index.html")