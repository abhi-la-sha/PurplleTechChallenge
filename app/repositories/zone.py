
import uuid

from sqlalchemy import select

from app.models.zone import Zone
from app.repositories.base import BaseRepository


class ZoneRepository(BaseRepository):
    async def create(self, zone: Zone) -> Zone:
        self._session.add(zone)
        await self._session.flush()
        await self._session.refresh(zone)
        return zone

    async def get_by_id(self, zone_id: uuid.UUID) -> Zone | None:
        return await self._session.get(Zone, zone_id)

    async def list_by_camera(self, camera_id: uuid.UUID) -> list[Zone]:
        stmt = (
            select(Zone)
            .where(Zone.camera_id == camera_id)
            .order_by(Zone.zone_name)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self) -> list[Zone]:
        stmt = select(Zone).order_by(Zone.zone_name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, zone: Zone) -> Zone:
        await self._session.flush()
        await self._session.refresh(zone)
        return zone

    async def delete(self, zone_id: uuid.UUID) -> bool:
        zone = await self.get_by_id(zone_id)
        if zone is None:
            return False
        await self._session.delete(zone)
        await self._session.flush()
        return True
