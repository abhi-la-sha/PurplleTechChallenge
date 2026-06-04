# Store Intelligence Platform

A computer-vision-powered retail analytics system that processes CCTV footage to generate footfall, zone engagement, queue, and conversion metrics for retail stores.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [CV Pipeline](#3-cv-pipeline)
4. [Backend & API](#4-backend--api)
5. [Data Model](#5-data-model)
6. [Analytics Endpoints](#6-analytics-endpoints)
7. [Event Types & Schema](#7-event-types--schema)
8. [Getting Started](#8-getting-started)
9. [Running Tests](#9-running-tests)
10. [Technology Choices](#10-technology-choices)
11. [Known Trade-offs](#11-known-trade-offs)
12. [Future Improvements](#12-future-improvements)

---

## 1. Overview

The Store Intelligence Platform ingests pre-recorded CCTV footage, detects and tracks customers through the store, and emits structured events (entry, zone engagement, queue joins, purchases) to a FastAPI backend. The backend stores events in PostgreSQL and exposes analytics APIs for footfall counts, conversion funnels, zone heatmaps, and anomaly detection.

**Key capabilities:**

- Real-time-equivalent per-frame person detection and tracking using YOLOv8n + ByteTrack
- Stable visitor identity across frames and brief re-entries via ReID embedding
- Staff vs. customer classification via HSV torso colour analysis
- Idempotent batch event ingestion with per-event error reporting
- On-demand analytics: conversion rate, funnel drop-off, zone heatmap, anomaly alerts
- Multi-store support with store-scoped metrics endpoints

---

## 2. Architecture

The platform is split into two independently runnable subsystems.

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
│  Routes → Services → Repositories → PostgreSQL 16               │
└──────────────────────────────────────────────────────────────────┘
```

### Backend layer responsibilities

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Routes | `app/api/routes/` | HTTP binding, Pydantic validation, dependency injection |
| Services | `app/services/` | Business rules (conversion rate, anomaly thresholds, funnel stages) |
| Repositories | `app/repositories/` | Async SQL queries — no formulas or business decisions |
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

| Revision | Description |
|----------|-------------|
| `001_phase1_initial` | Empty schema baseline |
| `002_phase2_domain_models` | cameras, zones, visitor_sessions, transactions, events, EventType enum |
| `003_add_store_id_is_staff` | `store_id` on events + visitor_sessions; `is_staff` on events |

---

## 3. CV Pipeline

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

### Processing flow

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

### Detection stage

`PersonTracker` wraps `ultralytics.YOLO` (yolov8n.pt) and `supervision.ByteTrack`. Inference is filtered to `class=0` (person) at `confidence ≥ 0.35`. Frame skipping (`SKIP_FRAMES = 3`) reduces computation by ~75%, running inference on every 4th frame while ByteTrack interpolates motion between tracked frames.

### Identity stage

`VisitorTracker` resolves ephemeral `track_id` integers to persistent `visitor_id` strings using a four-step cascade:

1. **Existing track** — reuse stored `visitor_id` directly.
2. **Re-entry by position** — if entry position is within `0.25` normalised units of a recently exited visitor (within 60 s), reuse their `visitor_id`.
3. **ReID by embedding** — cosine similarity against stored 32×64 greyscale crop embeddings; match threshold `0.85`.
4. **New visitor** — assign a fresh `VIS_{md5_hex}` identifier.

### Staff detection stage

`StaffDetector` examines the torso region (30–70% of bounding box height) in HSV colour space:

- **`dark` method (Store 1 — black uniform):** V-channel < 70 for > 40% of torso pixels.
- **`hue` method (Store 2 — pink uniform):** hue in [145, 175] for > 30% of valid (S ≥ 100, V ≥ 80) torso pixels.

Staff events are stored in the database but excluded from all visitor-facing metrics.

### Event logic

| Video type | Detection mechanism | Events generated |
|------------|---------------------|-----------------|
| `entry` | `LineCrossingDetector` — horizontal line at configurable `line_y` (default 0.50) | `ENTRY`, `EXIT` |
| `zone` | Foot-point inside a configured rectangular region | `ZONE_ENTER`, `ZONE_EXIT`, `ZONE_DWELL` (every 30 s while inside) |
| `billing` | Foot-point inside billing region | `BILLING_QUEUE_JOIN`, `BILLING_QUEUE_ABANDON` |

### Annotated video output

Each processed video produces an annotated MP4 in `analysis_frames/{store_id}/` with bounding boxes (green = customer, orange = staff), track/visitor ID labels, confidence scores, entry/exit line (red), billing region boundary (blue), and per-frame overlay stats.

---

## 4. Backend & API

### Ingestion

`POST /events/ingest` accepts batches of up to 500 events and returns `{ ingested, duplicates, errors }`. The endpoint is idempotent — the CV pipeline's client-generated UUID is the database primary key. Submitting a duplicate batch silently skips existing events without error, making retries safe.

### Store-scoped endpoints

All analytics endpoints accept a `store_id` path parameter. Repository-level filtering ensures no cross-store data is loaded into memory.

### Dependency injection

All route handlers receive `AsyncSession`, repositories, and services via FastAPI's `Depends()`. Unit tests replace these via `app.dependency_overrides`.

### Structured logging

`StructuredLoggingMiddleware` emits one JSON log line per HTTP request via the Starlette middleware stack.

### API documentation

Interactive OpenAPI docs are auto-generated at `/docs` from route annotations and Pydantic schemas.

---

## 5. Data Model

### Entity-relationship overview

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

### Key tables

**events** (central fact table)

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | client-provided for idempotency |
| store_id | VARCHAR(64) INDEX | added in migration 003 |
| visitor_id | VARCHAR(64) INDEX | |
| camera_id | UUID FK nullable | |
| zone_id | UUID FK nullable | |
| session_id | UUID FK nullable | |
| event_type | ENUM INDEX | see EventType enum below |
| timestamp | TIMESTAMPTZ INDEX | when the event occurred in the video |
| is_staff | BOOL | staff flag from CV pipeline |
| confidence | FLOAT | detector confidence 0–1 |
| metadata_json | JSONB | type-specific payload |
| created_at | TIMESTAMPTZ | append-only |

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

**transactions**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| transaction_id | VARCHAR UNIQUE | encoded as `{store_id}\|{txn_id}` for store scoping |
| transaction_timestamp | TIMESTAMPTZ | |
| basket_value | NUMERIC | ≥ 0 |
| visitor_session_id | UUID FK nullable | |

---

## 6. Analytics Endpoints

### `GET /stores/{store_id}/metrics`

Returns aggregate metrics for a store:

| Metric | Computation |
|--------|-------------|
| `unique_visitors` | COUNT non-staff visitor_sessions |
| `conversion_rate` | (converted / unique_visitors) × 100 |
| `average_dwell_ms` | AVG dwell from ZONE_DWELL metadata |
| `queue_depth` | COUNT active BILLING_QUEUE_JOIN without paired ABANDON |
| `abandonment_rate` | (abandoned / joined) × 100 |
| `average_basket_value` | AVG basket_value from transactions |

All floats are rounded to 2 decimal places. Division is safe (returns 0.0 when denominator is zero).

### `GET /stores/{store_id}/funnel`

Counts per funnel stage with drop-off percentages between stages:

```
ENTRY → ZONE_ENTER → BILLING_QUEUE_JOIN → PURCHASE
```

Drop-off % = `(prev_stage − this_stage) / prev_stage × 100`

### `GET /stores/{store_id}/heatmap`

Zone visit counts and average dwell time, with popularity normalised linearly to 0–100 against the most-visited zone. `data_confidence` is `false` for zones with fewer than 20 sessions.

### `GET /stores/{store_id}/anomalies`

| Anomaly | Trigger | Severities |
|---------|---------|------------|
| `BILLING_QUEUE_SPIKE` | queue depth ≥ 5 (WARN) or ≥ 10 (CRITICAL) | WARN, CRITICAL |
| `CONVERSION_DROP` | conversion < rolling average by ≥ 20% (WARN) or ≥ 40% (CRITICAL) | WARN, CRITICAL |
| `DEAD_ZONE` | no zone events within configured window | INFO, WARN |

### `GET /health`

Per-store feed freshness check. Returns `STALE_FEED` if no events received in the last 10 minutes.

### `GET /metrics` (global)

Global aggregate across all stores.

---

## 7. Event Types & Schema

### EventType enum

| Value | Source camera | Key `metadata_json` fields |
|-------|---------------|---------------------------|
| `ENTRY` | STORE_00x_CAM_ENTRY | `direction`, `source_video` |
| `EXIT` | STORE_00x_CAM_ENTRY | `direction` |
| `ZONE_ENTER` | CAM_ZONE_* | `zone_id`, `source_video` |
| `ZONE_EXIT` | CAM_ZONE_* | `zone_id` |
| `ZONE_DWELL` | CAM_ZONE_* | `zone_id`, `dwell_ms` |
| `BILLING_QUEUE_JOIN` | CAM_BILLING | `queue_position` |
| `BILLING_QUEUE_ABANDON` | CAM_BILLING | `dwell_ms` |
| `PURCHASE` | POS correlation | `transaction_id`, `basket_value` |
| `REENTRY` | any entry camera | `previous_session_id` |

### Event log JSONL format

Events are emitted by the CV pipeline and logged in JSONL format (one JSON object per line). The schema varies by event type:

**Entry / Exit events**
```json
{
  "event_type": "entry",
  "id_token": "ID_60001",
  "store_code": "store_1076",
  "camera_id": "cam1",
  "event_timestamp": "2026-03-08T18:10:05.120000",
  "is_staff": false,
  "gender_pred": "F",
  "age_pred": 28,
  "age_bucket": "25-34",
  "is_face_hidden": false,
  "group_id": null,
  "group_size": null
}
```

**Zone enter / exit events**
```json
{
  "event_type": "zone_entered",
  "track_id": 101,
  "store_id": "ST1076",
  "camera_id": "CAM2",
  "zone_id": "PURPLLE_MUM_1076_Z01",
  "zone_name": "Left Shelf",
  "zone_type": "SHELF",
  "is_revenue_zone": "Yes",
  "event_time": "2026-03-08T18:10:45.280000",
  "zone_hotspot_x": 412.6,
  "zone_hotspot_y": 238.4,
  "gender": "F",
  "age": 28,
  "age_bucket": "25-34"
}
```

**Queue completed / abandoned events**
```json
{
  "queue_event_id": "cfd8e3c5-7aa0-4ea3-9b59-692d50da8308",
  "event_type": "queue_completed",
  "track_id": 102,
  "store_id": "ST1076",
  "camera_id": "PURPLLE_MUM_1076_CAM6",
  "zone_id": "PURPLLE_MUM_1076_Z_BILLING_01",
  "zone_name": "Billing Counter Queue",
  "zone_type": "BILLING",
  "is_revenue_zone": "Yes",
  "queue_join_ts": "2026-03-08T18:13:05.080000",
  "queue_served_ts": "2026-03-08T18:13:13.240000",
  "queue_exit_ts": "2026-03-08T18:15:31.840000",
  "wait_seconds": 8,
  "queue_position_at_join": 2,
  "abandoned": false,
  "zone_hotspot_x": 602.8,
  "zone_hotspot_y": 183.4,
  "gender": "M",
  "age": 31,
  "age_bucket": "25-34"
}
```

---

## 8. Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- `pip install ultralytics supervision fastapi sqlalchemy alembic pydantic`

### Start the backend

```bash
docker compose up --build
```

This starts:
- `api` on `http://localhost:8000` (FastAPI + Uvicorn)
- `postgres` on `localhost:5432` (PostgreSQL 16)

### Run Alembic migrations

```bash
alembic upgrade head
```

### Run the CV pipeline

```bash
python cv/batch_runner.py
```

Configure store and video paths in `cv/config.py` before running.

### Interactive API docs

Visit `http://localhost:8000/docs` for the auto-generated OpenAPI UI.

---

## 9. Running Tests

Tests use Pytest with FastAPI's `dependency_overrides` to inject mock repositories and services — no live database required.

```bash
pytest
```

---

## 10. Technology Choices

| Component | Choice | Key reason |
|-----------|--------|-----------|
| Object detection | YOLOv8n | Real-time CPU throughput; 6 MB model; clean Supervision integration |
| Multi-object tracking | ByteTrack (via Supervision) | Two-stage matching handles occlusion without an appearance model |
| Backend framework | FastAPI | Native async, Pydantic v2 integration, auto OpenAPI docs |
| Database | PostgreSQL 16 | JSONB for metadata, UUID PKs, ACID guarantees, Alembic ENUM support |
| ORM | SQLAlchemy 2 (async) | `AsyncSession` for non-blocking DB access |
| Schema validation | Pydantic v2 | Shared by FastAPI routes and ORM `model_validate()` |
| Migrations | Alembic | Native PostgreSQL ENUM management |
| Containerisation | Docker Compose | Portable developer and CI environment |
| Testing | Pytest + dependency overrides | Mock injection without a live database |

See [CHOICES.md](CHOICES.md) for full rationale and alternatives considered.

---

## 11. Known Trade-offs

**YOLOv8n accuracy vs. speed** — The nano model trades detection accuracy for CPU-compatible throughput. Missed detections in low-light or occluded scenes are acceptable for aggregate footfall counting; per-person journey reconstruction would require a heavier model.

**On-demand analytics** — All metrics are computed per API request from raw event rows. This is fast for small-to-medium volumes but will degrade at millions of events; materialised views or pre-aggregation would be required at scale.

**Single-table event model** — The unified `events` table simplifies queries but produces sparse JSONB rows. High event volumes may require partitioning by `event_type` or `timestamp`.

**Staff detection by colour** — HSV thresholding is fast and tunable but brittle to lighting changes or uniform colour variation. A learned classifier would generalise better.

**No real-time streaming** — The current architecture processes pre-recorded video files. Live CCTV would require a streaming ingestion path and real-time anomaly triggers.

**Store ID in transactions** — `store_id` is encoded into the `transaction_id` column as `{store_id}|{txn_id}` rather than a dedicated column. This is a pragmatic workaround; a future migration should normalise it.

---

## 12. Future Improvements

### Computer Vision
- Upgrade to YOLOv8s/m for improved accuracy on GPU hardware
- Dedicated re-ID model (OSNet, CLIP) for cross-camera visitor matching
- Live RTSP stream processing
- Trained staff classifier to replace HSV thresholding
- Zone polygon editor for store managers

### Backend & API
- Materialised metric views or TimescaleDB hypertables for analytics at scale
- Proper `store_id` column on transactions (remove composite key encoding)
- `stores` table with name, timezone, and operating hours
- JWT-based authentication per store
- Event streaming to Kafka or Redis Streams for real-time downstream consumers
- Webhook alerts for anomaly events

### Infrastructure
- PgBouncer connection pooling for high-concurrency deployments
- Horizontal FastAPI scaling behind a load balancer
- CI/CD pipeline for automated test runs and Docker image builds
- Prometheus / OpenTelemetry metrics exporter and distributed tracing

### Analytics
- Conversion attribution correlating `BILLING_QUEUE_JOIN` with POS transactions by timestamp
- Re-entry analytics for first-time vs. returning visitor segmentation
- Cross-store comparison for chain-level dashboards
- Time-bucketed metrics API (hourly/daily/weekly) for trend charts