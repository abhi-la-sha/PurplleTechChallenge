
import uuid

from sqlalchemy import select

from app.models.camera import Camera
from app.repositories.base import BaseRepository


class CameraRepository(BaseRepository):
    async def create(self, camera: Camera) -> Camera:
        self._session.add(camera)
        await self._session.flush()
        await self._session.refresh(camera)
        return camera

    async def get_by_id(self, camera_id: uuid.UUID) -> Camera | None:
        return await self._session.get(Camera, camera_id)

    async def get_by_code(self, camera_code: str) -> Camera | None:
        stmt = select(Camera).where(Camera.camera_code == camera_code)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, *, active_only: bool = False) -> list[Camera]:
        stmt = select(Camera).order_by(Camera.camera_code)
        if active_only:
            stmt = stmt.where(Camera.is_active.is_(True))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, camera: Camera) -> Camera:
        await self._session.flush()
        await self._session.refresh(camera)
        return camera

    async def delete(self, camera_id: uuid.UUID) -> bool:
        camera = await self.get_by_id(camera_id)
        if camera is None:
            return False
        await self._session.delete(camera)
        await self._session.flush()
        return True
