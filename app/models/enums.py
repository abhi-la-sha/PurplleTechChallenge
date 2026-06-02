
from enum import StrEnum


class EventType(StrEnum):
    """All event types stored in the central events table."""

    ENTRY = "ENTRY"
    EXIT = "EXIT"
    ZONE_ENTER = "ZONE_ENTER"
    ZONE_EXIT = "ZONE_EXIT"
    ZONE_DWELL = "ZONE_DWELL"
    BILLING_QUEUE_JOIN = "BILLING_QUEUE_JOIN"
    BILLING_QUEUE_ABANDON = "BILLING_QUEUE_ABANDON"
    PURCHASE = "PURCHASE"
    REENTRY = "REENTRY"
