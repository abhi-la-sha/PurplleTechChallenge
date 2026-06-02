# Metrics API (Phase 4)

## Purpose

Phase 4 exposes store KPIs computed from persisted database records. Metrics are derived only from:

- `visitor_sessions`
- `transactions`

No computer vision, event-level analytics, caching, or background workers are used.

---

## Architecture Flow

```text
GET /metrics
    ↓
app/api/routes/metrics.py
    ↓
MetricsService
    ↓
MetricsRepository
    ↓
PostgreSQL (visitor_sessions, transactions)
```

---

## Endpoint

### `GET /metrics`

Returns aggregate store KPIs.

**Status:** `200 OK`

**Sample response:**

```json
{
  "total_visitors": 100,
  "converted_visitors": 25,
  "conversion_rate": 25.0,
  "average_dwell_time_seconds": 420.5,
  "average_basket_value": 863.75
}
```

---

## KPI Definitions

| KPI | Source | Formula |
|-----|--------|---------|
| `total_visitors` | `visitor_sessions` | `COUNT(visitor_sessions.id)` |
| `converted_visitors` | `visitor_sessions` | `COUNT(id WHERE converted = true)` |
| `conversion_rate` | service layer | `(converted_visitors / total_visitors) * 100` |
| `average_dwell_time_seconds` | `visitor_sessions.session_duration_seconds` | `AVG(session_duration_seconds)` excluding NULL |
| `average_basket_value` | `transactions.basket_value` | `AVG(basket_value)` |

### Division-by-zero and NULL handling

- If `total_visitors = 0`, `conversion_rate = 0.0`
- If no completed dwell values exist, `average_dwell_time_seconds = 0.0`
- If no transactions exist, `average_basket_value = 0.0`
- All float KPI values are rounded to **2 decimal places** in the service layer

---

## Layer Responsibilities

### Repository (`app/repositories/metrics.py`)

Executes aggregation queries only:

- `get_total_visitors()`
- `get_converted_visitors()`
- `get_average_dwell_time()`
- `get_average_basket_value()`

Returns raw aggregate values. No KPI formulas.

### Service (`app/services/metrics.py`)

Contains business logic:

- conversion rate calculation
- safe division handling
- NULL normalization to `0.0`
- rounding to 2 decimals
- `MetricsResponse` construction

### Route (`app/api/routes/metrics.py`)

Thin controller:

- injects `MetricsService`
- calls `get_metrics()`
- returns `MetricsResponse`

---

## Placeholder Endpoints (unchanged)

The following remain **501 Not Implemented**:

- `/heatmap`
- `/funnel`
- `/anomalies`

---

## Future Extensibility

Later phases can extend metrics by:

- adding filtered query parameters (date range, store id)
- introducing event-based analytics in dedicated endpoints
- adding funnel/heatmap/anomaly services without changing Phase 4 schema

Phase 4 intentionally keeps KPI scope limited to session and transaction aggregates.
