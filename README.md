# Store Intelligence Platform — Phase 1

Backend foundation for transforming CCTV footage into store intelligence. Phase 1 provides a runnable FastAPI service, PostgreSQL integration, migrations, Docker, and tests — without CV, events, metrics, or dashboards.

## Architecture

```
Route → Service → Repository → Database
```

| Layer        | Responsibility                          |
|-------------|------------------------------------------|
| `app/api`   | HTTP routes, dependency injection        |
| `app/services` | Business orchestration (Phase 2+)     |
| `app/repositories` | Data access                        |
| `app/models` | SQLAlchemy ORM (base only in Phase 1) |
| `app/schemas` | Pydantic v2 request/response models   |
| `app/core`  | Config, structured JSON logging          |
| `app/db`    | Async engine and sessions                |

## Prerequisites

- Python 3.12+
- Docker & Docker Compose (recommended)
- PostgreSQL 16 (if running locally without Docker)

## Setup (local)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Start PostgreSQL (or use Docker Compose for the `postgres` service only), then run migrations:

```bash
alembic upgrade head
```

Run the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Docker usage

Build and start API + PostgreSQL:

```bash
docker compose up --build
```

API: http://localhost:8000  
Interactive docs: http://localhost:8000/docs

Run migrations inside the API container:

```bash
docker compose exec api alembic upgrade head
```

Stop services:

```bash
docker compose down
```

## API endpoints (Phase 1)

| Method | Path        | Status | Response |
|--------|-------------|--------|----------|
| GET    | `/`         | 200    | `{"service":"store-intelligence-api","version":"0.1.0"}` |
| GET    | `/health`   | 200    | `{"status":"healthy"}` |
| *      | `/events`   | 501    | Not Implemented |
| *      | `/metrics`  | 501    | Not Implemented |
| *      | `/funnel`   | 501    | Not Implemented |
| *      | `/anomalies`| 501    | Not Implemented |
| *      | `/heatmap`  | 501    | Not Implemented |

## Run tests

```bash
pip install -r requirements.txt
pytest -v
```

Tests use dependency overrides and do not require a running database.

## Project layout

```
app/
  api/           # Routes and DI
  core/          # Config, logging, middleware
  db/            # Async SQLAlchemy session
  models/        # ORM base classes (no domain entities yet)
  repositories/
  schemas/
  services/
alembic/         # Migrations
tests/
```

## Phase 2 — Domain model

SQLAlchemy models, Pydantic schemas, repositories, and migration `002_phase2_domain_models` are in place. See [docs/DATA_MODEL.md](docs/DATA_MODEL.md) for entities, relationships, and event flow.

```bash
alembic upgrade head
```

## Future phases

Phase 3 adds event ingestion via `/events`. Analytics plug into existing route modules without restructuring the foundation.

## Optional: video inspection (Phase 0)

```bash
pip install -r requirements-cv.txt
python inspect_videos.py
```
