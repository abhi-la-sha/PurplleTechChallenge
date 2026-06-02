
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.camera import Camera
    from app.models.event import Event


class Zone(BaseModel):
    """Logical retail zone defined on a camera view."""

    __tablename__ = "zones"
    __table_args__ = (
        UniqueConstraint("camera_id", "zone_name", name="uq_zones_camera_id_zone_name"),
    )

    camera_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zone_name: Mapped[str] = mapped_column(String(128), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    polygon_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    camera: Mapped[Camera] = relationship(back_populates="zones")
    events: Mapped[list[Event]] = relationship(back_populates="zone")
