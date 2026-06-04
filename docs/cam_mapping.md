# Video Mapping

This project does not use fixed camera identifiers.

The provided dataset consists of offline video footage grouped by store and business purpose.

---

# Store 1

Store ID:

STORE_001

Staff Uniform:

Black

Videos:

## entry.mp4

Purpose:

Entry Monitoring

Generated Events:

* ENTRY
* EXIT

---

## zone1.mp4

Purpose:

Zone Analytics

Zone ID:

ZONE_1

Generated Events:

* ZONE_ENTER
* ZONE_EXIT
* ZONE_DWELL

---

## zone2.mp4

Purpose:

Zone Analytics

Zone ID:

ZONE_2

Generated Events:

* ZONE_ENTER
* ZONE_EXIT
* ZONE_DWELL

---

## billing_area.mp4

Purpose:

Billing Analytics

Generated Events:

* BILLING_QUEUE_JOIN
* BILLING_QUEUE_ABANDON

---

# Store 2

Store ID:

STORE_002

Staff Uniform:

Pink

Videos:

## entry1.mp4

Purpose:

Entry Monitoring

Zone ID:

ENTRY_1

Generated Events:

* ENTRY
* EXIT

---

## entry2.mp4

Purpose:

Entry Monitoring

Zone ID:

ENTRY_2

Generated Events:

* ENTRY
* EXIT

---

## zone.mp4

Purpose:

Zone Analytics

Zone ID:

ZONE

Generated Events:

* ZONE_ENTER
* ZONE_EXIT
* ZONE_DWELL

---

## billing_area.mp4

Purpose:

Billing Analytics

Generated Events:

* BILLING_QUEUE_JOIN
* BILLING_QUEUE_ABANDON

---

# Event Summary

The Computer Vision Pipeline generates the following event types:

## Entry Analytics

* ENTRY
* EXIT

## Zone Analytics

* ZONE_ENTER
* ZONE_EXIT
* ZONE_DWELL

## Billing Analytics

* BILLING_QUEUE_JOIN
* BILLING_QUEUE_ABANDON

---

# Staff Detection

Store-specific staff identification is used.

STORE_001

* Black uniform

STORE_002

* Pink uniform

Staff events are stored but excluded from:

* Footfall metrics
* Funnel analytics
* Conversion analytics
* Visitor counts

---

# Annotated Outputs

All processed videos generate annotated outputs in:

analysis_frames/

store1/
store2/

Outputs include:

* Bounding boxes
* Track IDs
* STAFF/CUSTOMER labels
* Event overlays
* Processing statistics

These videos are used for validation, debugging, and demonstration.
