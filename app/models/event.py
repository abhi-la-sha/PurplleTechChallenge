from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import UUIDPrimaryKeyMixin
from app.models.enums import EventType

if TYPE_CHECKING:
    from app.models.camera import Camera
    from app.models.visitor_session import VisitorSession
    from app.models.zone import Zone


class Event(Base, UUIDPrimaryKeyMixin):
    """Unified event record; type-specific fields live in metadata_json."""

    __tablename__ = "events"

    store_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", index=True
    )
    visitor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cameras.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("zones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("visitor_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[EventType] = mapped_column(
        Enum(
            EventType,
            name="event_type_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    is_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    camera: Mapped[Camera | None] = relationship(back_populates="events")
    zone: Mapped[Zone | None] = relationship(back_populates="events")
    session: Mapped[VisitorSession | None] = relationship(back_populates="events")