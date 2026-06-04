# CHOICES.md — Store Intelligence Platform

## Table of Contents

1. [Technology Decisions Overview](#1-technology-decisions-overview)
2. [YOLOv8n Selection](#2-yolov8n-selection)
3. [ByteTrack Selection](#3-bytetrack-selection)
4. [FastAPI Rationale](#4-fastapi-rationale)
5. [PostgreSQL Rationale](#5-postgresql-rationale)
6. [Schema Design Decisions](#6-schema-design-decisions)
7. [API Architecture Decisions](#7-api-architecture-decisions)
8. [Trade-offs](#8-trade-offs)
9. [Future Improvements](#9-future-improvements)

---

## 1. Technology Decisions Overview

| Component | Choice | Alternatives Considered |
|-----------|--------|------------------------|
| Object detection | YOLOv8n | YOLOv5, Faster R-CNN, MobileNet-SSD |
| Multi-object tracking | ByteTrack (via Supervision) | DeepSORT, StrongSORT, OC-SORT |
| Backend framework | FastAPI | Flask, Django REST Framework |
| Database | PostgreSQL 16 | MySQL, SQLite, MongoDB |
| ORM | SQLAlchemy 2 (async) | Tortoise ORM, raw asyncpg |
| Schema validation | Pydantic v2 | Marshmallow, dataclasses |
| Migrations | Alembic | Django migrations, Flyway |
| Containerisation | Docker Compose | Kubernetes, bare-metal |
| Testing | Pytest + dependency overrides | unittest |

---

## 2. YOLOv8n Selection

**Model chosen:** `yolov8n.pt` (YOLOv8 nano variant from Ultralytics)

### Reasons for selection

**Speed on CPU hardware.** The nano variant was selected because the CV pipeline must run on commodity hardware without a GPU. YOLOv8n achieves real-time throughput on CPU at the resolution required for store CCTV footage, while heavier variants (YOLOv8s/m/l/x) would produce unacceptable processing times for multi-hour video files.

**Person detection accuracy.** YOLOv8n achieves sufficient mean average precision for the person class (COCO class 0) in retail CCTV conditions — moderate resolution, partially occluded subjects, mixed lighting. False negatives are preferable to false positives in a counting system because over-counting inflates footfall metrics more harmfully than under-counting.

**Ecosystem integration.** Ultralytics provides a clean Python API (`YOLO.predict()`) with native `supervision` library compatibility. `sv.Detections.from_ultralytics()` converts inference results to the Supervision detection format with one call, making ByteTrack integration seamless.

**Single model file.** The pre-trained `yolov8n.pt` file ships as a 6 MB self-contained model, requiring no separate configuration files, anchor definitions, or class maps.

**Frame skipping compatibility.** YOLOv8n's fast per-frame inference makes frame skipping (`SKIP_FRAMES = 3`) a practical optimisation — running inference on every 4th frame reduces overall processing time by ~75% while ByteTrack interpolates motion between tracked frames.

### Why not other options

- **YOLOv5** — older architecture, less accurate at same model size, less maintained.
- **Faster R-CNN** — two-stage detector with high accuracy but 5–10× slower inference; impractical for batch video processing on CPU.
- **MobileNet-SSD** — faster but significantly lower accuracy on partially occluded persons in complex scenes.

---

## 3. ByteTrack Selection

**Tracker chosen:** ByteTrack via the `supervision` library (`sv.ByteTrack`)

### Reasons for selection

**Detection-confidence-aware association.** ByteTrack's core innovation is the two-stage matching scheme: high-confidence detections are matched first; low-confidence detections are then used to recover occluded tracks. This dramatically reduces ID switches compared to trackers that discard low-confidence detections entirely (e.g. SORT), making it well-suited to retail environments where partial occlusion by shelving and other customers is common.

**No appearance model required at the tracker level.** ByteTrack uses IoU-based Kalman filter matching rather than deep appearance embeddings at the track association step. This keeps CPU requirements low. Appearance-based re-identification is handled separately by `VisitorTracker` using the lightweight greyscale crop embedding, keeping concerns cleanly separated.

**Stable track IDs within a continuous video segment.** ByteTrack maintains track IDs across brief disappearances (up to several frames), which is critical for accurate zone dwell time accumulation. Without this, a person momentarily obscured by shelving would generate spurious ZONE_EXIT/ZONE_ENTER pairs.

**Supervision library integration.** The `supervision` library provides `ByteTrack` with a consistent API (`tracker.update_with_detections(detections)`) that works directly with `sv.Detections` objects. This eliminates the need to write custom tracker adapters.

**Proven retail and surveillance performance.** ByteTrack was benchmarked on MOT17 and MOT20 datasets with performance competitive with or exceeding DeepSORT while being faster, making it the practical choice for this use case.

### Why not other options

- **DeepSORT** — requires a deep appearance model (re-ID network) at the tracking level, significantly increasing CPU overhead and adding a second model dependency.
- **StrongSORT** — more accurate but heavier than ByteTrack; the accuracy gain is marginal for the head-count and zone analytics required here.
- **OC-SORT** — strong performance but less widely packaged and tested in the Supervision ecosystem at time of development.

---

## 4. FastAPI Rationale

### Reasons for selection

**Native async support.** The entire backend is async-first (`async def` route handlers, `AsyncSession` from SQLAlchemy). FastAPI is built on Starlette and ASGI, making it the natural choice. Flask and Django REST Framework require third-party async extensions that add complexity without equivalent community support.

**Pydantic v2 integration.** FastAPI's request/response validation is built on Pydantic v2, which is already the project's schema library. Schema classes in `app/schemas/` are used both for FastAPI validation and for ORM model validation via `model_validate()`, eliminating the need for a second serialisation layer.

**Automatic interactive documentation.** The OpenAPI spec at `/docs` is generated automatically from route type annotations and Pydantic schemas. This provides up-to-date API documentation without manual maintenance and was used throughout development for manual endpoint testing.

**Dependency injection system.** FastAPI's `Depends()` mechanism is used throughout the project to inject `AsyncSession`, repositories, and services into route handlers. This made writing unit tests straightforward — repositories and services are replaced with mocks via `app.dependency_overrides` in the test suite.

**Performance.** FastAPI benchmarks consistently among the fastest Python web frameworks. For a backend primarily constrained by database query time, raw HTTP throughput is not the limiting factor, but avoiding framework overhead keeps latency low for live-dashboard use cases.

**Structured logging middleware.** The `StructuredLoggingMiddleware` in `app/core/middleware.py` integrates cleanly with Starlette's middleware stack, emitting JSON log lines per request with minimal boilerplate.

---

## 5. PostgreSQL Rationale

### Reasons for selection

**JSONB for event metadata.** The `metadata_json` column on the `events` table stores type-specific fields (zone_id string, dwell_ms, queue_position, basket_value, etc.) as JSONB. PostgreSQL's JSONB type supports indexed lookups and containment queries on the JSON payload, enabling future queries like "all ZONE_DWELL events where dwell_ms > 60000" without schema changes.

**UUID primary keys.** PostgreSQL natively supports the `UUID` type, which is used as the primary key for all tables. UUIDs are generated by the CV pipeline and passed as `event_id` values, making idempotent ingestion straightforward — the CV pipeline controls the identity of each event rather than relying on a database sequence.

**Window functions for analytics.** Future anomaly detection queries (e.g. rolling conversion average for `CONVERSION_DROP`) benefit from PostgreSQL's window function support. The current analytics are aggregate-query-based but are designed to be extended with `OVER (PARTITION BY ...)` clauses without changing the schema.

**Alembic migration support.** SQLAlchemy/Alembic has first-class PostgreSQL support, including the ability to create and manage native PostgreSQL `ENUM` types, which is used for the `event_type_enum` enum column on the events table.

**ACID compliance and production readiness.** Retail analytics requires reliable event counts. PostgreSQL's transactional semantics guarantee that a batch ingest either fully commits or fully rolls back, preventing partial event counts from corrupting metrics.

**Docker availability.** The official `postgres:16` Docker image is well-maintained and widely deployed, making the Docker Compose setup portable across developer machines and CI environments.

### Why not other options

- **SQLite** — no concurrent writes, no JSONB, not suitable for production deployment.
- **MySQL** — weaker JSONB support, less expressive window functions, more complex async driver ecosystem.
- **MongoDB** — document store would simplify event metadata but loses ACID guarantees, makes aggregate analytics (AVG, COUNT) less efficient, and introduces a second query language.

---

## 6. Schema Design Decisions

### Single events table

All event types are stored in a single `events` table rather than separate tables per event type. This allows aggregate queries (total events, funnel stages, heatmap) to operate on a single table scan with `WHERE event_type = '...'` filters backed by an index.

The trade-off is that type-specific fields live in `metadata_json` rather than typed columns. For the current analytics requirements (counts, averages, time-range filters), this is sufficient. If specific fields needed frequent indexed access, promoting them to dedicated columns via migration would be straightforward.

### Client-provided UUID as primary key

The CV pipeline generates a `uuid.uuid4()` `event_id` for each event before sending it to the API. The API stores this as the primary key. This enables idempotent ingestion: submitting the same batch twice produces no duplicates because the second insert on a conflicting UUID is detected via `get_existing_ids()` and skipped.

The alternative — a server-generated sequence or UUID with a separate `event_id` unique index — would require a two-column lookup for duplicate detection and would make the CV pipeline unable to reference a specific event by a stable identifier.

### JSONB over EAV or typed columns

Type-specific event fields (e.g. `dwell_ms` for ZONE_DWELL, `queue_position` for BILLING_QUEUE_JOIN) are stored in `metadata_json` as JSONB rather than as nullable typed columns or an entity-attribute-value (EAV) table. JSONB was chosen because:

- New event types require no schema migration.
- Occasional reads by metadata field are supported via PostgreSQL JSONB operators.
- EAV tables are notoriously complex to query for aggregate analytics.

### Store ID added via migration

`store_id` was not in the original Phase 2 schema and was added in migration `003`. The `store_id` field on `events` is a plain VARCHAR rather than a foreign key to a `stores` table, which avoids the need to pre-seed store rows before events can be ingested. A stores table can be introduced in a future migration if richer store metadata is required.

### Store scope encoding in transactions

The Phase 2 `transactions` table has no `store_id` column. Rather than adding a migration in Phase 5, the service encodes store scope into the unique `transaction_id` column as `{store_id}|{transaction_id}`. The service layer transparently encodes on write and decodes on read. This was a deliberate pragmatic trade-off to avoid a schema migration mid-phase; a future migration should normalise this into a proper `store_id` column.

---

## 7. API Architecture Decisions

### Clean architecture layering

The Route → Service → Repository → Database layering enforces a strict rule: no SQL in service code, no business logic in repository code, and no database access in route handlers. This separation was chosen to:

- Make unit testing possible without a database (dependency overrides inject mock repositories).
- Allow the analytics logic (conversion rate, safe division, anomaly thresholds) to be tested independently of SQL.
- Keep routes thin so that adding a new transport layer (e.g. gRPC, WebSocket) would require only new route handlers, not service refactoring.

### Async-first

All database access uses `AsyncSession` from `sqlalchemy.ext.asyncio`. Route handlers are `async def`. This ensures the Uvicorn worker thread is never blocked waiting for a database query, which is critical when the CV pipeline submits high-volume batch ingests concurrently with dashboard API calls.

### Dependency injection via `Depends()`

Repositories and services are constructed inside `Depends()` factories rather than as module-level singletons. This makes every request handler receive a fresh `AsyncSession` bound to the request lifetime, preventing session sharing across requests and simplifying connection pool management.

### Idempotent batch ingestion endpoint

`POST /events/ingest` accepts batches of up to 500 events and returns `{ ingested, duplicates, errors }`. The design choices are:

- **Batch rather than single-event endpoint** — reduces HTTP round-trips from the CV pipeline from hundreds to a handful per video.
- **Silent duplicate skipping** — the CV pipeline retries on network failure; silent skipping rather than error on duplicates means retries are safe without special handling.
- **Per-event error reporting** — individual malformed events return an error item rather than failing the whole batch, so one bad event does not discard an entire flush buffer.

### Store-scoped metrics endpoints

`GET /stores/{store_id}/metrics` was added alongside the global `GET /metrics` to support multi-store deployments. All store-scoped endpoints filter by `store_id` at the repository level, not in the service layer, so no cross-store data is ever loaded into memory.

---

## 8. Trade-offs

### YOLOv8n accuracy vs speed

Using the nano model means lower detection accuracy compared to YOLOv8s or YOLOv8m. In low-light or heavily occluded scenes, person detections may be missed. For the current use case (footfall counting, zone analytics), moderate miss rates are acceptable because metrics are based on aggregates across many frames. A higher-accuracy model would be appropriate if precise per-person tracking (e.g. individual customer journey reconstruction) becomes a requirement.

### On-demand analytics vs materialised metrics

All metrics are computed by querying the `events` and `visitor_sessions` tables on each API request. For small to medium event volumes this is fast and requires no background infrastructure. For large datasets (millions of events), response times will degrade and materialised aggregates or time-series pre-computation will become necessary.

### Single-table event model

The unified `events` table simplifies queries and schema evolution but produces sparse rows for type-specific fields (many JSONB keys are null for most event types). For very high event volumes, partitioning by `event_type` or by `timestamp` range may be needed.

### Staff detection by colour

HSV colour thresholding is fast and tunable but brittle. Changes to uniform colour, lighting conditions, or store environments require manual reconfiguration. A learned classifier (fine-tuned on store-specific images) would generalise better but adds a training dependency.

### No real-time streaming

The current architecture processes pre-recorded video files in batch mode. Live CCTV feeds would require a streaming ingestion path (e.g. frame queue, RTSP capture) and real-time anomaly triggers rather than query-time anomaly detection.

---

## 9. Future Improvements

### Computer Vision

- **Upgrade to YOLOv8s or YOLOv8m** for improved accuracy where GPU hardware is available.
- **Re-ID with a dedicated model** (e.g. OSNet or CLIP-based embedding) to improve cross-camera visitor identity matching.
- **Live RTSP stream processing** to replace batch video files and enable real-time event emission.
- **Trained staff classifier** to replace HSV thresholding and handle diverse uniform colours, lighting variation, and mixed-garment scenarios.
- **Zone polygon editor** to allow store managers to configure zone boundaries via a UI rather than hardcoded coordinates in `config.py`.

### Backend and API

- **Materialised metric views or time-series pre-aggregation** (e.g. TimescaleDB hypertables) to keep analytics queries fast as event volume grows.
- **Proper `store_id` column on transactions** by normalising away the encoded composite key.
- **`stores` table** for richer store metadata (name, timezone, operating hours) and foreign key integrity.
- **Authentication and authorisation** — the current API has no auth layer. JWT-based auth per store would be needed before production deployment.
- **Event streaming output** — publish events to Kafka or Redis Streams so downstream consumers (real-time dashboard, alert engine) can react without polling the API.
- **Webhook alerts** for anomaly events so store managers receive push notifications rather than polling `/anomalies`.

### Infrastructure

- **Database connection pooling tuning** — PgBouncer in front of PostgreSQL for high-concurrency deployments.
- **Horizontal scaling** — the stateless FastAPI service can scale horizontally behind a load balancer; the main constraint is the database connection pool.
- **CI/CD pipeline** — automated test runs and Docker image builds on push; currently tests are run manually.
- **Observability** — structured logs are in place but no metrics exporter (Prometheus/OpenTelemetry) or distributed tracing (Jaeger) is implemented.

### Analytics

- **Conversion attribution** — correlate `BILLING_QUEUE_JOIN` events with POS transactions by timestamp proximity to compute a more accurate session-level conversion flag.
- **Re-entry analytics** — track `REENTRY` events to distinguish first-time vs returning visitors.
- **Cross-store comparison** — aggregate metrics across all stores for chain-level dashboards.
- **Historical trend API** — time-bucketed metrics (hourly/daily/weekly) for trend charts.