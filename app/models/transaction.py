
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.visitor_session import VisitorSession


class Transaction(BaseModel):
    """POS transaction record for conversion correlation."""

    __tablename__ = "transactions"

    transaction_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )
    transaction_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    basket_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    visitor_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("visitor_sessions.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )

    session: Mapped[VisitorSession | None] = relationship(back_populates="transaction")
