"""Health check data access (extensible for DB probes in later phases)."""

from sqlalchemy import text

from app.repositories.base import BaseRepository


class HealthRepository(BaseRepository):
    """Repository for health-related infrastructure checks."""

    async def ping_database(self) -> bool:
        """Verify database connectivity."""
        result = await self._session.execute(text("SELECT 1"))
        return result.scalar_one() == 1
