from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.transaction import Transaction


class VisitorSession(BaseModel):

    __tablename__ = "visitor_sessions"

    store_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", index=True
    )
    visitor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    session_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    converted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    events: Mapped[list[Event]] = relationship(back_populates="session")
    transaction: Mapped[Transaction | None] = relationship(
        back_populates="session",
        uselist=False,
    )