"""Base repository for data access layer."""

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """Shared session holder for repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session
