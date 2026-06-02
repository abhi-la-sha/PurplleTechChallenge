# Transactions API (Phase 5)

## Purpose

Phase 5 adds POS transaction ingestion and retrieval. Transactions represent completed purchases and will later support conversion attribution and funnel analytics.

This phase only persists and queries transactions. No conversion matching, metrics changes, or CV logic are included.

---

## Architecture Flow

```text
POST/GET /transactions
    ↓
app/api/routes/transactions.py
    ↓
TransactionService
    ↓
TransactionRepository
    ↓
PostgreSQL (transactions)
```

---

## Endpoints

### `POST /transactions`

Create one transaction.

**Request:**

```json
{
  "store_id": "STORE_BLR_002",
  "transaction_id": "TXN_001",
  "timestamp": "2026-03-03T14:38:12Z",
  "basket_value": 1240.50
}
```

**Response:** `201 Created` with `TransactionRead`

**Errors:**

- `409 Conflict` — duplicate `transaction_id` (per store scope)
- `422 Unprocessable Entity` — invalid payload (negative basket value, invalid timestamp)

---

### `POST /transactions/bulk`

Create multiple transactions in one request.

**Request:**

```json
{
  "transactions": [
    {
      "store_id": "STORE_BLR_002",
      "transaction_id": "TXN_001",
      "timestamp": "2026-03-03T14:38:12Z",
      "basket_value": 1240.50
    }
  ]
}
```

**Response:**

```json
{
  "created": 1
}
```

---

### `GET /transactions/{transaction_id}`

Fetch by business transaction ID (for example `TXN_001`).

- `200 OK` — transaction found
- `404 Not Found` — transaction does not exist

---

### `GET /transactions`

List transactions with optional filters and pagination.

**Query parameters:**

- `store_id`
- `start_time`
- `end_time`
- `limit` (default `100`)
- `offset` (default `0`)

**Ordering:** `timestamp DESC`

**Response:**

```json
{
  "items": [],
  "total": 0
}
```

---

## Validation Rules

| Field | Rule |
|-------|------|
| `store_id` | required, non-empty |
| `transaction_id` | required, unique per store |
| `timestamp` | required, valid datetime |
| `basket_value` | required, `>= 0` |

---

## Store ID Persistence (No Schema Change)

Phase 2 `transactions` table has no `store_id` column. To avoid schema migration in Phase 5, the service encodes store scope into the existing `transaction_id` column as:

```text
{store_id}|{transaction_id}
```

API responses decode this value back into separate `store_id` and `transaction_id` fields.

---

## Layer Responsibilities

### Repository

- `create()`
- `create_many()`
- `get_by_transaction_id()`
- `list()`
- `count()`
- `exists()`

Aggregation and business formulas are not allowed in repository code.

### Service

- duplicate detection (`409`)
- not-found handling (`404`)
- bulk orchestration
- encode/decode store scope for persistence

### Route

- inject `TransactionService`
- return typed schemas
- no DB access or calculations

---

## Future Usage

Later phases will use ingested transactions for:

- conversion attribution to `visitor_sessions`
- funnel stage completion
- abandonment analysis
- enriched store KPIs

Phase 5 intentionally stops at reliable ingestion and retrieval.
