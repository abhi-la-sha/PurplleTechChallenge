"""ORM model instantiation tests."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.models.camera import Camera
from app.models.enums import EventType
from app.models.event import Event
from app.models.transaction import Transaction
from app.models.visitor_session import VisitorSession
from app.models.zone import Zone


def test_camera_model_fields() -> None:
    camera = Camera(
        camera_name="Entry Camera",
        camera_code="CAM3",
        purpose="Entry / Exit Monitoring",
        is_active=True,
    )
    assert camera.camera_code == "CAM3"
    assert camera.is_active is True
    assert camera.__tablename__ == "cameras"


def test_zone_model_polygon_json() -> None:
    zone = Zone(
        camera_id=uuid.uuid4(),
        zone_name="ENTRY_ZONE",
        zone_type="entry",
        polygon_json={"points": [[0, 0], [100, 0], [100, 50], [0, 50]]},
    )
    assert "points" in zone.polygon_json


def test_visitor_session_model() -> None:
    session = VisitorSession(
        visitor_id="visitor-abc-001",
        entry_time=datetime.now(UTC),
        converted=False,
    )
    assert session.visitor_id == "visitor-abc-001"
    assert session.converted is False


def test_transaction_model() -> None:
    txn = Transaction(
        transaction_id="POS-1001",
        transaction_timestamp=datetime.now(UTC),
        basket_value=Decimal("1299.00"),
    )
    assert txn.basket_value == Decimal("1299.00")


def test_event_model_metadata() -> None:
    event = Event(
        visitor_id="visitor-abc-001",
        event_type=EventType.ZONE_DWELL,
        timestamp=datetime.now(UTC),
        metadata_json={"zone_id": str(uuid.uuid4()), "dwell_seconds": 42},
        confidence=0.91,
    )
    assert event.event_type == EventType.ZONE_DWELL
    assert event.metadata_json["dwell_seconds"] == 42
