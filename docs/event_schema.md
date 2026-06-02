# Event Schema

## Common Fields

All events contain:

* event_id
* visitor_id
* camera_id
* timestamp
* confidence
* metadata_json

---

## ENTRY

Generated when a visitor crosses the entry line into the store.

Additional Fields:

* direction

---

## EXIT

Generated when a visitor leaves the store.

Additional Fields:

* direction

---

## ZONE_ENTER

Generated when a visitor enters a defined retail zone.

Additional Fields:

* zone_id

---

## ZONE_EXIT

Generated when a visitor exits a defined retail zone.

Additional Fields:

* zone_id

---

## ZONE_DWELL

Generated periodically while a visitor remains inside a zone.

Additional Fields:

* zone_id
* dwell_seconds

---

## BILLING_QUEUE_JOIN

Generated when a visitor enters the billing queue.

Additional Fields:

* queue_position

---

## BILLING_QUEUE_ABANDON

Generated when a visitor leaves the queue without completing checkout.

Additional Fields:

* dwell_seconds

---

## PURCHASE

Generated after successful transaction correlation.

Additional Fields:

* transaction_id
* basket_value

---

## REENTRY

Generated when a visitor returns within a configurable time window.

Additional Fields:

* previous_session_id
