
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.zone import Zone


class Camera(BaseModel):
    """CCTV camera registered in the platform."""

    __tablename__ = "cameras"

    camera_name: Mapped[str] = mapped_column(String(128), nullable=False)
    camera_code: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        unique=True,
        index=True,
    )
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    zones: Mapped[list[Zone]] = relationship(
        back_populates="camera",
        cascade="all, delete-orphan",
    )
    events: Mapped[list[Event]] = relationship(back_populates="camera")
