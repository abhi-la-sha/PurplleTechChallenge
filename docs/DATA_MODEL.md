# Data Model — Store Intelligence Platform (Phase 2)

## Overview

Phase 2 defines the persistent domain model for an **event-driven** retail analytics platform. All future metrics (footfall, dwell, conversion, funnel, anomalies) are derived from rows in the central `events` table — not from hardcoded counters.

No computer vision, ingestion APIs, or analytics logic exist in this phase.

---

## Design Principles

| Principle | Implementation |
|-----------|----------------|
| Event-driven | Single `events` table for every `EventType` |
| Extensibility | Type-specific fields in `metadata_json` per `docs/event_schema.md` |
| Multi-camera | `cameras` + `zones` with flexible polygons |
| Multi-day / reprocessing | Immutable events with timestamps; no destructive updates required |
| POS correlation | `transactions` optionally linked to `visitor_sessions` |
| Re-ID (future) | Shared `visitor_id` string across events and sessions |

---

## Entity Relationship Diagram

```mermaid
erDiagram
    CAMERAS ||--o{ ZONES : defines
    CAMERAS ||--o{ EVENTS : captures
    ZONES ||--o{ EVENTS : contextualizes
    VISITOR_SESSIONS ||--o{ EVENTS : groups
    VISITOR_SESSIONS |o--o| TRANSACTIONS : may_convert_to

    CAMERAS {
        uuid id PK
        string camera_name
        string camera_code UK
        text purpose
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }

    ZONES {
        uuid id PK
        uuid camera_id FK
        string zone_name
        string zone_type
        jsonb polygon_json
        timestamptz created_at
        timestamptz updated_at
    }

    VISITOR_SESSIONS {
        uuid id PK
        string visitor_id
        timestamptz entry_time
        timestamptz exit_time
        int session_duration_seconds
        boolean converted
        timestamptz created_at
        timestamptz updated_at
    }

    TRANSACTIONS {
        uuid id PK
        string transaction_id UK
        timestamptz transaction_timestamp
        numeric basket_value
        uuid visitor_session_id FK UK
        timestamptz created_at
        timestamptz updated_at
    }

    EVENTS {
        uuid id PK
        string visitor_id
        uuid camera_id FK
        uuid zone_id FK
        uuid session_id FK
        enum event_type
        timestamptz timestamp
        float confidence
        jsonb metadata_json
        timestamptz created_at
    }
```

---

## Entities

### Camera

Represents a physical CCTV feed (e.g. CAM1–CAM5).

| Field | Description |
|-------|-------------|
| `camera_code` | Stable identifier (`CAM1`, `CAM3`, …), **unique** |
| `purpose` | Human-readable role (product analytics, entry, billing) |
| `is_active` | Supports decommissioning without data loss |

**Relationships:** one camera → many zones, many events.

---

### Zone

Logical retail region on a camera view (e.g. `LEFT_PRODUCT_ZONE`, `BILLING_ZONE`).

| Field | Description |
|-------|-------------|
| `polygon_json` | Arbitrary polygon definition (points, coordinate system, labels) |
| `zone_type` | Category string for analytics grouping |

**Constraints:** unique `(camera_id, zone_name)`.

**Relationships:** belongs to one camera; referenced by events.

---

### VisitorSession

One store visit for a tracked `visitor_id` (assigned by the CV pipeline in later phases).

| Field | Description |
|-------|-------------|
| `entry_time` / `exit_time` | Session boundaries |
| `session_duration_seconds` | Populated when exit is known |
| `converted` | Set when correlated with a purchase (Phase 8) |

**Relationships:** many events; zero or one transaction.

---

### Transaction

POS sale record for conversion and funnel analytics.

| Field | Description |
|-------|-------------|
| `transaction_id` | External POS identifier, **unique** |
| `basket_value` | Purchase amount |
| `visitor_session_id` | Optional link after correlation |

---

### Event

**Central fact table.** Every business signal is stored here.

| Field | Description |
|-------|-------------|
| `event_type` | `EventType` enum (see below) |
| `visitor_id` | Tracker ID (indexed) |
| `camera_id` / `zone_id` / `session_id` | Optional foreign keys |
| `timestamp` | When the event occurred (indexed) |
| `confidence` | Detector confidence (0–1) |
| `metadata_json` | Type-specific payload per `docs/event_schema.md` |

**Note:** Events have `created_at` only (append-only audit trail).

**Indexes:** `visitor_id`, `event_type`, `timestamp`, composite `(visitor_id, timestamp)`.

---

## EventType Enum

| Value | Typical source | Metadata examples |
|-------|----------------|-------------------|
| `ENTRY` | CAM3 | `direction` |
| `EXIT` | CAM3 | `direction` |
| `ZONE_ENTER` | CAM1, CAM2 | `zone_id` |
| `ZONE_EXIT` | CAM1, CAM2 | `zone_id` |
| `ZONE_DWELL` | CAM1, CAM2 | `zone_id`, `dwell_seconds` |
| `BILLING_QUEUE_JOIN` | CAM5 | `queue_position` |
| `BILLING_QUEUE_ABANDON` | CAM5 | `dwell_seconds` |
| `PURCHASE` | POS correlation | `transaction_id`, `basket_value` |
| `REENTRY` | Future re-ID | `previous_session_id` |

---

## Event Flow (Conceptual)

```
CCTV / CV Pipeline (Phase 4+)
        │
        ▼
   Event rows (Phase 3 ingestion)
        │
        ├──► VisitorSession updates (entry/exit)
        ├──► Zone analytics (Phase 6)
        ├──► Billing queue metrics (Phase 7)
        └──► POS correlation → Transaction link (Phase 8)
                │
                ▼
        Metrics / Funnel / Anomalies (Phase 5, 8, 9)
```

---

## Layer Mapping (Clean Architecture)

| Layer | Phase 2 artifacts |
|-------|-------------------|
| Models | `app/models/` |
| Schemas | `app/schemas/` (Base, Create, Read) |
| Repositories | `app/repositories/` (CRUD only) |
| Services | Phase 3+ (ingestion, analytics) |
| Routes | Phase 3+ (existing placeholders return 501) |

---

## Future Extensibility

- **New event types:** extend `EventType` enum + Alembic migration; still one `events` table.
- **New cameras/zones:** insert rows; no schema change.
- **Multiple stores:** add `store_id` to `cameras` (or a `stores` table) without redesigning events.
- **Reprocessing:** insert new events with batch metadata; sessions can be recomputed idempotently by pipeline version in `metadata_json`.
- **Live streaming:** same ingestion path as batch; timestamp-ordered queries use existing indexes.

---

## Migration

Apply Phase 2 schema:

```bash
alembic upgrade head
```

Revision: `002_phase2_domain_models` (depends on `001_phase1_initial`).
