
from app.repositories.health import HealthRepository
from app.schemas.health import HealthResponse


class HealthService:
    """Application health orchestration."""

    def __init__(self, repository: HealthRepository) -> None:
        self._repository = repository

    async def get_health(self) -> HealthResponse:
        """Return service health (Phase 1: static healthy response)."""
        # Repository available for future DB-dependent health checks.
        _ = self._repository
        return HealthResponse()
