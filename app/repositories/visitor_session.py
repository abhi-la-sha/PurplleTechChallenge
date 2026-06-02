
import uuid

from sqlalchemy import select

from app.models.visitor_session import VisitorSession
from app.repositories.base import BaseRepository


class VisitorSessionRepository(BaseRepository):
    async def create(self, session: VisitorSession) -> VisitorSession:
        self._session.add(session)
        await self._session.flush()
        await self._session.refresh(session)
        return session

    async def get_by_id(self, session_id: uuid.UUID) -> VisitorSession | None:
        return await self._session.get(VisitorSession, session_id)

    async def list_by_visitor(self, visitor_id: str) -> list[VisitorSession]:
        stmt = (
            select(VisitorSession)
            .where(VisitorSession.visitor_id == visitor_id)
            .order_by(VisitorSession.entry_time.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self) -> list[VisitorSession]:
        stmt = select(VisitorSession).order_by(VisitorSession.entry_time.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, session: VisitorSession) -> VisitorSession:
        await self._session.flush()
        await self._session.refresh(session)
        return session

    async def delete(self, session_id: uuid.UUID) -> bool:
        session = await self.get_by_id(session_id)
        if session is None:
            return False
        await self._session.delete(session)
        await self._session.flush()
        return True
