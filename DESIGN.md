# DESIGN.md — Store Intelligence Platform

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Event Flow](#2-event-flow)
3. [Analytics Architecture](#3-analytics-architecture)
4. [CV Pipeline](#4-cv-pipeline)
5. [Data Model](#5-data-model)
6. [AI-Assisted Decisions](#6-ai-assisted-decisions)

---

## 1. System Architecture

The platform is split into two independently runnable subsystems: a **FastAPI backend** that stores, validates, and serves analytics, and a **Computer Vision pipeline** that processes CCTV footage and feeds events into the backend.

```
┌──────────────────────────────────────────────────────────────────┐
│                        CV Pipeline (offline)                     │
│                                                                  │
│  CCTV Videos ──► YOLOv8n ──► ByteTrack ──► Event Logic ──►      │
│                  (detect)    (track)    (entry/zone/billing)     │
│                                              │                   │
│                      StaffDetector ──────────┘                   │
│                      (HSV uniform colour)                        │
└────────────────────────────┬─────────────────────────────────────┘
                             │  POST /events/ingest  (batched, retry)
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                              │
│                                                                  │
│  HTTP Request                                                    │
│       │                                                          │
│       ▼                                                          │
│  app/api/routes/   (thin controllers, DI)                        │
│       │                                                          │
│       ▼                                                          │
│  app/services/     (business logic, safe-division, rounding)     │
│       │                                                          │
│       ▼                                                          │
│  app/repositories/ (async SQLAlchemy queries, no logic)          │
│       │                                                          │
│       ▼                                                          │
│  PostgreSQL 16     (events, visitor_sessions, transactions, …)   │
└──────────────────────────────────────────────────────────────────┘
```

### Backend layer responsibilities

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Routes | `app/api/routes/` | HTTP binding, Pydantic validation, dependency injection |
| Services | `app/services/` | Business rules (conversion rate, anomaly thresholds, funnel stages) |
| Repositories | `app/repositories/` | Async SQL queries; no formulas or business decisions |
| Models | `app/models/` | SQLAlchemy ORM declarations |
| Schemas | `app/schemas/` | Pydantic v2 request/response contracts |
| Core | `app/core/` | Settings, structured JSON logging, middleware |
| DB | `app/db/` | Async engine, session factory, lifespan management |

### Deployed topology

```
Docker Compose
├── api       (FastAPI + Uvicorn, port 8000)
└── postgres  (PostgreSQL 16, port 5432)
```

Schema migrations are managed by **Alembic** with three sequential revisions:
`001_phase1_initial` → `002_phase2_domain_models` → `003_add_store_id_is_staff`.

---

## 2. Event Flow

All analytics are derived from a single `events` fact table. No hardcoded counters exist anywhere in the system.

### End-to-end flow

```
CCTV footage
    │
    ▼
batch_runner.py  ──  iterates every VideoConfig per store
    │
    ├── PersonTracker (YOLOv8n + ByteTrack)
    │       returns list[TrackedPerson] per frame
    │
    ├── StaffDetector
    │       classifies each person as CUSTOMER or STAFF
    │       via torso HSV analysis
    │
    ├── VisitorTracker
    │       maps tracker IDs → stable visitor_id strings
    │       re-entry / ReID via position + embedding cosine similarity
    │
    ├── Event logic (per video type)
    │   ├── entry video  →  LineCrossingDetector → ENTRY / EXIT events
    │   ├── zone video   →  polygon presence     → ZONE_ENTER / ZONE_EXIT / ZONE_DWELL
    │   └── billing video→  region presence      → BILLING_QUEUE_JOIN / BILLING_QUEUE_ABANDON
    │
    └── EventEmitter
            buffers CVEvent objects
            POST /events/ingest  (batches of 50, up to 3 retries)
            idempotent: client-generated UUID as primary key
```

### Ingestion API flow

```
POST /events/ingest
    │
    ▼
EventService.ingest_batch()
    ├── fetch existing event_ids from DB   (duplicate check)
    ├── build Event ORM objects for new IDs only
    └── EventRepository.create_many()
            └── bulk INSERT into events table
                    │
                    ▼
            IngestResponse { ingested, duplicates, errors }
```

### Downstream analytics flow

```
events table
    │
    ├── GET /stores/{store_id}/metrics
    │       MetricsRepository → visitor_sessions + transactions aggregates
    │       MetricsService    → conversion rate, abandonment rate, safe division
    │
    ├── GET /stores/{store_id}/funnel
    │       MetricsRepository → count events per funnel stage
    │       MetricsService    → drop-off percentages between stages
    │       Stages: ENTRY → ZONE_ENTER → BILLING_QUEUE_JOIN → PURCHASE
    │
    ├── GET /stores/{store_id}/heatmap
    │       MetricsRepository → zone visit counts + avg dwell per zone
    │       MetricsService    → normalised popularity score 0–100
    │                          data_confidence=false if < 20 sessions
    │
    ├── GET /stores/{store_id}/anomalies
    │       BILLING_QUEUE_SPIKE  — queue depth > threshold (WARN/CRITICAL)
    │       CONVERSION_DROP      — conversion below rolling average
    │       DEAD_ZONE            — no zone activity within window (INFO/WARN)
    │
    └── GET /health
            per-store feed freshness check
            STALE_FEED if no events in > 10 minutes
```

---

## 3. Analytics Architecture

### Metric computation

All metrics are computed on-demand from persisted database rows. There are no background workers, materialised views, or cached counters in the current implementation.

```
GET /stores/{store_id}/metrics
────────────────────────────────
MetricsRepository queries
  • get_store_unique_visitors()     — COUNT non-staff visitor_sessions
  • get_store_converted_visitors()  — COUNT sessions WHERE converted = true
  • get_store_average_dwell_ms()    — AVG dwell from ZONE_DWELL events metadata
  • get_store_queue_depth()         — COUNT active BILLING_QUEUE_JOIN without paired ABANDON
  • get_store_abandonment_counts()  — COUNT BILLING_QUEUE_ABANDON vs JOIN
  • get_store_average_basket_value()— AVG basket_value from transactions

MetricsService computes
  • conversion_rate   = (converted / unique_visitors) × 100  — safe division
  • abandonment_rate  = (abandoned / joined) × 100           — safe division
  • all floats rounded to 2 decimal places
```

### Funnel analytics

Stages are ordered ENTRY → ZONE_ENTER → BILLING_QUEUE_JOIN → PURCHASE. Each stage is counted independently from the `events` table filtered by `store_id` and `event_type`. Drop-off percentage is computed as `(prev_stage - this_stage) / prev_stage × 100`.

### Heatmap analytics

Zone popularity is derived from ZONE_ENTER and ZONE_DWELL events. Each zone receives a raw visit count and average dwell time. Scores are then normalised linearly to 0–100 against the most-visited zone. `data_confidence` is set to `false` for zones with fewer than 20 sessions.

### Anomaly detection

| Anomaly | Trigger | Severities |
|---------|---------|------------|
| `BILLING_QUEUE_SPIKE` | queue depth ≥ 5 (WARN) or ≥ 10 (CRITICAL) | WARN, CRITICAL |
| `CONVERSION_DROP` | current rate < rolling average by ≥ 20% (WARN) or ≥ 40% (CRITICAL) | WARN, CRITICAL |
| `DEAD_ZONE` | no zone events within configured window | INFO, WARN |

---

## 4. CV Pipeline

### Module map

```
cv/
├── config.py        — YOLO params, store/video mappings, staff colour configs
├── detect.py        — PersonTracker: YOLOv8n inference + ByteTrack via Supervision
├── tracker.py       — VisitorTracker: track_id → visitor_id, re-entry, ReID
├── staff.py         — StaffDetector: torso crop + HSV colour classification
├── emit.py          — EventEmitter: CVEvent dataclass, buffered POST with retries
├── utils.py         — LineCrossingDetector, VideoAnnotator, OverlayStats, geometry helpers
└── batch_runner.py  — Orchestrator: per-store, per-video processing loop
```

### Detection stage

`PersonTracker` wraps `ultralytics.YOLO` (yolov8n.pt) and `supervision.ByteTrack`. Each call to `update(frame)` runs inference filtered to `class=0` (person) at `confidence ≥ 0.35`, converts detections to `sv.Detections`, feeds them through ByteTrack, and returns a list of `TrackedPerson` objects with stable `track_id`, bounding box, confidence, and a lightweight appearance embedding (32×64 greyscale crop, L2-normalised).

Frame skipping (`SKIP_FRAMES = 3`) reduces computation: inference is run on every 4th frame; intermediate frames are skipped without resetting tracker state.

### Tracking and identity stage

`VisitorTracker` translates ephemeral integer `track_id` values (which reset when a person leaves the frame) into persistent `visitor_id` strings:

1. **Existing track** — reuse stored `visitor_id` directly.
2. **Re-entry by position** — if the entry position is within `0.25` normalised units of a recently exited visitor (within 60 s), reuse their `visitor_id`.
3. **ReID by embedding** — cosine similarity against stored embeddings; match at threshold `0.85`.
4. **New visitor** — assign a fresh `VIS_{md5_hex}` identifier.

`mark_exit()` moves a track to the `_recently_exited` list; `_prune_exits()` removes entries older than the reentry window.

### Staff detection stage

`StaffDetector` examines the torso region (30–70% of bounding box height) in HSV colour space. Two methods are supported per store:

- **`dark` method (Store 1 — black uniform):** fraction of pixels with V-channel < 70 must exceed 40%.
- **`hue` method (Store 2 — pink uniform):** fraction of valid pixels (S ≥ 100, V ≥ 80) whose hue falls in [145, 175] must exceed 30%.

Staff events are stored in the database but excluded from all visitor-facing metrics, funnel analytics, and conversion calculations.

### Event logic stage

| Video type | Detection mechanism | Events generated |
|------------|--------------------|--------------------|
| `entry` | `LineCrossingDetector` — horizontal line at configurable `line_y` (default 0.50); direction determined by y-movement sign, inverted per-camera | `ENTRY`, `EXIT` |
| `zone` | Foot-point inside a configured rectangular region | `ZONE_ENTER`, `ZONE_EXIT`, `ZONE_DWELL` (every 30 s while inside) |
| `billing` | Foot-point inside billing region | `BILLING_QUEUE_JOIN`, `BILLING_QUEUE_ABANDON` |

### Emission stage

`EventEmitter` buffers `CVEvent` dicts and flushes to `POST /events/ingest` when the buffer reaches 50 events or at explicit `flush()` on video end. Retry logic: up to 3 attempts with linear back-off (2 s × attempt). Duplicate prevention relies on the client-provided `event_id` UUID stored as the database primary key.

### Annotated video output

Each processed video produces an annotated MP4 in `analysis_frames/{store_id}/`. The `VideoAnnotator` draws:

- Bounding boxes coloured green (customer) or orange (staff)
- Track ID and visitor ID label
- Detection confidence
- STAFF / CUSTOMER classification
- Entry/exit line (red)
- Billing region boundary (blue)
- Per-frame overlay: active tracks, unique visitor count, staff count, event count

---

## 5. Data Model

### Entity-relationship diagram

```
CAMERAS ──────────────┬──────────── ZONES
   │                  │               │
   │ (1:many)         │ (1:many)      │ (1:many)
   │                  │               │
EVENTS ◄──────────────┴───────────────┘
   │
   │ (many:1)
VISITOR_SESSIONS
   │
   │ (1:0..1)
TRANSACTIONS
```

### Table definitions

**cameras**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| camera_name | VARCHAR(128) | human label |
| camera_code | VARCHAR(32) UNIQUE | stable code e.g. `STORE_001_CAM_ENTRY` |
| purpose | TEXT | product analytics / entry / billing |
| is_active | BOOL | soft decommission |
| created_at / updated_at | TIMESTAMPTZ | |

**zones**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| camera_id | UUID FK → cameras | |
| zone_name | VARCHAR(128) | unique per camera |
| zone_type | VARCHAR(64) | grouping category |
| polygon_json | JSONB | arbitrary polygon coordinates |
| created_at / updated_at | TIMESTAMPTZ | |

**visitor_sessions**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| visitor_id | VARCHAR(64) | assigned by CV pipeline |
| store_id | VARCHAR(64) | added in migration 003 |
| entry_time | TIMESTAMPTZ | |
| exit_time | TIMESTAMPTZ | nullable until exit |
| session_duration_seconds | INT | populated on exit |
| converted | BOOL | set when POS correlation succeeds |
| created_at / updated_at | TIMESTAMPTZ | |

**transactions**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| transaction_id | VARCHAR UNIQUE | encoded as `{store_id}\|{txn_id}` for store scoping |
| transaction_timestamp | TIMESTAMPTZ | |
| basket_value | NUMERIC | ≥ 0 |
| visitor_session_id | UUID FK → visitor_sessions | nullable |
| created_at / updated_at | TIMESTAMPTZ | |

**events** (central fact table)

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | client-provided for idempotency |
| store_id | VARCHAR(64) INDEX | added in migration 003 |
| visitor_id | VARCHAR(64) INDEX | |
| camera_id | UUID FK nullable | |
| zone_id | UUID FK nullable | |
| session_id | UUID FK nullable | |
| event_type | ENUM INDEX | ENTRY, EXIT, ZONE_ENTER, ZONE_EXIT, ZONE_DWELL, BILLING_QUEUE_JOIN, BILLING_QUEUE_ABANDON, PURCHASE, REENTRY |
| timestamp | TIMESTAMPTZ INDEX | when the event occurred in the video |
| is_staff | BOOL | staff flag carried through from CV |
| confidence | FLOAT | detector confidence 0–1 |
| metadata_json | JSONB | type-specific payload (zone_id string, dwell_ms, queue_position, etc.) |
| created_at | TIMESTAMPTZ | append-only; no updated_at |

**Indexes:** `visitor_id`, `event_type`, `timestamp`, `store_id`, composite `(visitor_id, timestamp)`.

### EventType enum

| Value | Primary source camera | Key metadata fields |
|-------|----------------------|---------------------|
| `ENTRY` | STORE_00x_CAM_ENTRY | `direction`, `source_video` |
| `EXIT` | STORE_00x_CAM_ENTRY | `direction` |
| `ZONE_ENTER` | CAM_ZONE_* | `zone_id`, `source_video` |
| `ZONE_EXIT` | CAM_ZONE_* | `zone_id` |
| `ZONE_DWELL` | CAM_ZONE_* | `zone_id`, `dwell_ms` |
| `BILLING_QUEUE_JOIN` | CAM_BILLING | `queue_position` |
| `BILLING_QUEUE_ABANDON` | CAM_BILLING | `dwell_ms` |
| `PURCHASE` | POS correlation | `transaction_id`, `basket_value` |
| `REENTRY` | any entry camera | `previous_session_id` |

### Migration history

| Revision | Description |
|----------|-------------|
| `001_phase1_initial` | Empty schema baseline |
| `002_phase2_domain_models` | cameras, zones, visitor_sessions, transactions, events, EventType enum |
| `003_add_store_id_is_staff` | `store_id` on events + visitor_sessions; `is_staff` on events |

---

## 6. AI-Assisted Decisions

The following design decisions were informed or validated with AI assistance during development:


### Re-entry and ReID architecture

The layered identity resolution (position → embedding cosine similarity → new visitor) was designed with AI assistance to handle the common CCTV scenario where a person briefly leaves and re-enters the frame. The lightweight 32×64 greyscale embedding was chosen over a full re-identification model as a pragmatic balance between accuracy and inference speed on CPU hardware.

### Idempotent ingestion design

The decision to use the client-provided UUID as the database primary key — rather than a secondary unique index — was validated with AI assistance. This approach eliminates a separate duplicate-check index, simplifies the ingest path, and guarantees idempotency without a two-phase lookup under most database isolation levels.

### `metadata_json` schema extensibility

Rather than creating type-specific event tables, AI assistance reinforced the single-table event design with a JSONB payload for type-specific fields. This keeps the query layer uniform while allowing each event type to carry arbitrary structured data without schema migrations.

### Store ID encoding in transactions

The decision to encode `store_id` into the `transaction_id` column as `{store_id}|{txn_id}` (avoiding a migration on the transactions table) was discussed and validated with AI assistance as a pragmatic Phase 5 workaround that preserves the existing unique constraint while adding store scoping.