
from fastapi import HTTPException, status


class PlaceholderService:
    """Raises 501 for future-phase endpoints."""

    async def not_implemented(self) -> None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Not Implemented",
        )
