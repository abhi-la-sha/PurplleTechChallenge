# Event API (Phase 3)

## Purpose

Phase 3 introduces the ingestion pipeline used by future CV modules.

Producer -> `POST /events` -> Validation -> Service -> Repository -> PostgreSQL

This phase only ingests and retrieves events. It does not compute analytics.

## Endpoints

### `POST /events`

Creates a single event.

Request:

```json
{
  "visitor_id": "visitor_001",
  "event_type": "ENTRY",
  "timestamp": "2026-06-01T10:00:00Z",
  "camera_id": null,
  "zone_id": null,
  "session_id": null,
  "confidence": 0.91,
  "metadata_json": {
    "source": "manual_test"
  }
}
```

Response (`201`):

```json
{
  "id": "c261b834-d2d7-43f1-852f-f98ded2a8f8f",
  "visitor_id": "visitor_001",
  "event_type": "ENTRY",
  "timestamp": "2026-06-01T10:00:00Z",
  "camera_id": null,
  "zone_id": null,
  "session_id": null,
  "confidence": 0.91,
  "metadata_json": {
    "source": "manual_test"
  },
  "created_at": "2026-06-01T10:00:00Z"
}
```

### `POST /events/bulk`

Creates multiple events in one request.

Request:

```json
{
  "events": [
    {
      "visitor_id": "visitor_001",
      "event_type": "ENTRY",
      "timestamp": "2026-06-01T10:00:00Z"
    },
    {
      "visitor_id": "visitor_001",
      "event_type": "ZONE_ENTER",
      "timestamp": "2026-06-01T10:00:10Z"
    }
  ]
}
```

Response (`200`):

```json
{
  "created_count": 2
}
```

### `GET /events/{event_id}`

Fetches one event by UUID.

- `200` with `EventRead`
- `404` when the event does not exist

### `GET /events`

Lists events with optional filters and pagination.

Query params:

- `visitor_id`
- `event_type`
- `camera_id`
- `zone_id`
- `session_id`
- `limit` (default 100)
- `offset` (default 0)

Default ordering: `timestamp DESC`

Response:

```json
{
  "items": [],
  "total": 0,
  "limit": 100,
  "offset": 0
}
```

### `GET /events/stats`

Ingestion-only count endpoint.

Response:

```json
{
  "total_events": 123
}
```

## Validation rules

- `visitor_id` is required
- `event_type` is required and must match `EventType` enum
- `timestamp` is required
- `confidence` is optional, but if present must be between `0.0` and `1.0`
- `metadata_json` is optional
- Invalid enum and invalid confidence return `422`

## Event lifecycle

1. Producer sends event payload.
2. FastAPI validates payload with Pydantic schemas.
3. Route delegates to `EventService`.
4. Service orchestrates `EventRepository`.
5. Repository persists rows in the `events` table.
6. API returns typed response schemas.

## Future CV integration notes

- Phase 4+ detectors (CAM3 entry/exit, YOLO + ByteTrack modules) should emit events through `POST /events` or `POST /events/bulk`.
- Keep type-specific detector details in `metadata_json`.
- Do not bypass the ingestion API for CV pipelines; this preserves validation and auditability.
