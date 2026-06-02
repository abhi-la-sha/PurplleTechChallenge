"""Pydantic schema serialization tests."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models.enums import EventType
from app.models.camera import Camera
from app.models.event import Event
from app.schemas.camera import CameraCreate, CameraRead
from app.schemas.event import EventCreate, EventRead
from app.schemas.transaction import TransactionCreate, TransactionRead


def test_camera_schema_round_trip() -> None:
    now = datetime.now(UTC)
    camera_id = uuid.uuid4()
    read = CameraRead(
        id=camera_id,
        camera_name="Product Camera 1",
        camera_code="CAM1",
        purpose="Product Analytics",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    assert read.camera_code == "CAM1"

    create = CameraCreate.model_validate(read.model_dump(exclude={"id", "created_at", "updated_at"}))
    assert create.camera_name == "Product Camera 1"


@pytest.mark.asyncio
async def test_camera_read_from_orm_attributes(db_session) -> None:
    from app.repositories.camera import CameraRepository

    camera = await CameraRepository(db_session).create(
        Camera(
            camera_name="Billing Camera",
            camera_code="CAM5",
            purpose="Billing Monitoring",
        )
    )
    schema = CameraRead.model_validate(camera)
    assert schema.camera_code == "CAM5"
    assert schema.id == camera.id


def test_event_schema_validation() -> None:
    payload = EventCreate(
        visitor_id="visitor-001",
        event_type=EventType.ENTRY,
        timestamp=datetime.now(UTC),
        metadata_json={"direction": "in"},
        confidence=0.95,
    )
    assert payload.event_type == EventType.ENTRY


@pytest.mark.asyncio
async def test_event_read_from_orm(db_session) -> None:
    from app.repositories.event import EventRepository

    event = await EventRepository(db_session).create(
        Event(
            visitor_id="visitor-002",
            event_type=EventType.PURCHASE,
            timestamp=datetime.now(UTC),
            metadata_json={"transaction_id": "POS-9", "basket_value": 500.0},
        )
    )
    read = EventRead.model_validate(event)
    assert read.event_type == EventType.PURCHASE


def test_transaction_schema() -> None:
    txn = TransactionCreate(
        transaction_id="TX-42",
        transaction_timestamp=datetime.now(UTC),
        basket_value=Decimal("42.50"),
    )
    read = TransactionRead(
        id=uuid.uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        **txn.model_dump(),
    )
    assert read.transaction_id == "TX-42"
