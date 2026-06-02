"""Relationship integrity tests with async persistence."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.camera import Camera
from app.models.enums import EventType
from app.models.event import Event
from app.models.transaction import Transaction
from app.models.visitor_session import VisitorSession
from app.models.zone import Zone
from app.repositories.camera import CameraRepository
from app.repositories.event import EventRepository
from app.repositories.transaction import TransactionRepository
from app.repositories.visitor_session import VisitorSessionRepository
from app.repositories.zone import ZoneRepository


@pytest.mark.asyncio
async def test_camera_zone_event_relationships(db_session: AsyncSession) -> None:
    camera_repo = CameraRepository(db_session)
    zone_repo = ZoneRepository(db_session)
    event_repo = EventRepository(db_session)

    camera = await camera_repo.create(
        Camera(camera_name="Cam 1", camera_code="CAM1", purpose="Product Analytics")
    )
    zone = await zone_repo.create(
        Zone(
            camera_id=camera.id,
            zone_name="LEFT_PRODUCT_ZONE",
            zone_type="product",
            polygon_json={"points": [[1, 1], [2, 2], [3, 3]]},
        )
    )
    event = await event_repo.create(
        Event(
            visitor_id="visitor-rel-001",
            camera_id=camera.id,
            zone_id=zone.id,
            event_type=EventType.ZONE_ENTER,
            timestamp=datetime.now(UTC),
            metadata_json={"zone_id": str(zone.id)},
        )
    )
    await db_session.commit()

    stmt = (
        select(Camera)
        .where(Camera.id == camera.id)
        .options(selectinload(Camera.zones), selectinload(Camera.events))
    )
    loaded = (await db_session.execute(stmt)).scalar_one()
    assert len(loaded.zones) == 1
    assert loaded.zones[0].zone_name == "LEFT_PRODUCT_ZONE"
    assert len(loaded.events) == 1
    assert loaded.events[0].id == event.id


@pytest.mark.asyncio
async def test_session_transaction_one_to_one(db_session: AsyncSession) -> None:
    session_repo = VisitorSessionRepository(db_session)
    txn_repo = TransactionRepository(db_session)

    visit = await session_repo.create(
        VisitorSession(
            visitor_id="visitor-rel-002",
            entry_time=datetime.now(UTC),
            converted=True,
        )
    )
    txn = await txn_repo.create(
        Transaction(
            transaction_id="POS-REL-001",
            transaction_timestamp=datetime.now(UTC),
            basket_value=Decimal("999.99"),
            visitor_session_id=visit.id,
        )
    )
    await db_session.commit()

    stmt = (
        select(VisitorSession)
        .where(VisitorSession.id == visit.id)
        .options(selectinload(VisitorSession.transaction))
    )
    loaded_session = (await db_session.execute(stmt)).scalar_one()
    assert loaded_session.transaction is not None
    assert loaded_session.transaction.id == txn.id


@pytest.mark.asyncio
async def test_session_events_relationship(db_session: AsyncSession) -> None:
    session_repo = VisitorSessionRepository(db_session)
    event_repo = EventRepository(db_session)

    visit = await session_repo.create(
        VisitorSession(
            visitor_id="visitor-rel-003",
            entry_time=datetime.now(UTC),
        )
    )
    await event_repo.create(
        Event(
            visitor_id=visit.visitor_id,
            session_id=visit.id,
            event_type=EventType.ENTRY,
            timestamp=datetime.now(UTC),
        )
    )
    await event_repo.create(
        Event(
            visitor_id=visit.visitor_id,
            session_id=visit.id,
            event_type=EventType.EXIT,
            timestamp=datetime.now(UTC),
        )
    )
    await db_session.commit()

    events = await event_repo.list_by_session(visit.id)
    assert len(events) == 2
    assert {event.event_type for event in events} == {EventType.ENTRY, EventType.EXIT}
