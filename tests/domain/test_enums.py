"""EventType enum tests."""

import pytest
from pydantic import BaseModel, ValidationError

from app.models.enums import EventType
from app.schemas.event import EventCreate


def test_event_type_contains_all_required_values() -> None:
    expected = {
        "ENTRY",
        "EXIT",
        "ZONE_ENTER",
        "ZONE_EXIT",
        "ZONE_DWELL",
        "BILLING_QUEUE_JOIN",
        "BILLING_QUEUE_ABANDON",
        "PURCHASE",
        "REENTRY",
    }
    assert {member.value for member in EventType} == expected


def test_event_type_is_str_enum() -> None:
    assert EventType.ENTRY == "ENTRY"
    assert isinstance(EventType.ZONE_DWELL, str)


def test_invalid_event_type_rejected_by_schema() -> None:
    class BadEvent(BaseModel):
        event_type: EventType

    with pytest.raises(ValidationError):
        BadEvent(event_type="INVALID")  # type: ignore[arg-type]
