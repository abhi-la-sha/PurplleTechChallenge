from datetime import datetime, timezone
from app.repositories.health import HealthRepository
from app.schemas.health import HealthResponse

STALE_THRESHOLD_MINUTES = 10

class HealthService:
    """Application health orchestration."""

    def __init__(self, repository: HealthRepository) -> None:
        self._repository = repository
   
    async def get_health(self) -> HealthResponse:
        stores = []
        rows = await self._repository.get_last_event_per_store()
        now = datetime.now(timezone.utc)
        for store_id, last_timestamp in rows:
            age_minutes = (now - last_timestamp).total_seconds() / 60
            feed_status = ("STALE_FEED" if age_minutes > STALE_THRESHOLD_MINUTES else "OK")
            stores.append(StoreHealth(store_id=store_id, last_event_timestamp=last_timestamp,feed_status=feed_status,))
        return HealthResponse(status="healthy",stores=stores,)
