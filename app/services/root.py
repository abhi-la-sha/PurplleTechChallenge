
from app.core.config import Settings
from app.schemas.root import RootResponse


class RootService:
    """Service metadata for API discovery."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_root(self) -> RootResponse:
        return RootResponse(
            service=self._settings.app_name,
            version=self._settings.app_version,
        )
