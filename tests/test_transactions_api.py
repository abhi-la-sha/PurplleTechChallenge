"""API tests for Phase 5 transaction ingestion endpoints."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from app.db.base import Base
from app.db.session import get_async_session
from app.main import create_app
from app.models import Camera, Event, Transaction, VisitorSession, Zone  # noqa: F401
from app.schemas.transaction import TransactionRead


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(_type: JSONB, compiler: object, **kwargs: object) -> str:
    return "JSON"


@pytest.fixture
async def transactions_client() -> AsyncIterator[tuple[AsyncClient, AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    session = session_factory()

    application = create_app()

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    application.dependency_overrides[get_async_session] = override_session
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, session

    application.dependency_overrides.clear()
    await session.close()
    await engine.dispose()


def _transaction_payload(
    *,
    store_id: str = "STORE_BLR_002",
    transaction_id: str = "TXN_001",
    timestamp: datetime | None = None,
    basket_value: float = 1240.50,
) -> dict[str, object]:
    return {
        "store_id": store_id,
        "transaction_id": transaction_id,
        "timestamp": (timestamp or datetime.now(UTC)).isoformat(),
        "basket_value": basket_value,
    }


@pytest.mark.asyncio
async def test_post_transaction_success(
    transactions_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _session = transactions_client
    response = await client.post("/transactions", json=_transaction_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["transaction_id"] == "TXN_001"
    assert data["store_id"] == "STORE_BLR_002"
    assert data["basket_value"] == "1240.50" or float(data["basket_value"]) == 1240.50


@pytest.mark.asyncio
async def test_post_transaction_duplicate_transaction_id(
    transactions_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _session = transactions_client
    payload = _transaction_payload()
    first = await client.post("/transactions", json=payload)
    assert first.status_code == 201

    duplicate = await client.post("/transactions", json=payload)
    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_post_transaction_invalid_basket_value(
    transactions_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _session = transactions_client
    response = await client.post(
        "/transactions",
        json=_transaction_payload(basket_value=-1.0),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_transaction_invalid_timestamp(
    transactions_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _session = transactions_client
    payload = _transaction_payload()
    payload["timestamp"] = "not-a-datetime"
    response = await client.post("/transactions", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_transactions_bulk_success(
    transactions_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _session = transactions_client
    payload = {
        "transactions": [
            _transaction_payload(transaction_id="TXN_001"),
            _transaction_payload(transaction_id="TXN_002"),
        ]
    }
    response = await client.post("/transactions/bulk", json=payload)
    assert response.status_code == 200
    assert response.json() == {"created": 2}


@pytest.mark.asyncio
async def test_post_transactions_bulk_invalid_payload(
    transactions_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _session = transactions_client
    payload = {
        "transactions": [
            _transaction_payload(transaction_id="TXN_OK"),
            _transaction_payload(transaction_id="TXN_BAD", basket_value=-5.0),
        ]
    }
    response = await client.post("/transactions/bulk", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_transaction_by_id_found(
    transactions_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _session = transactions_client
    created = await client.post(
        "/transactions",
        json=_transaction_payload(transaction_id="TXN_LOOKUP"),
    )
    assert created.status_code == 201

    response = await client.get("/transactions/TXN_LOOKUP")
    assert response.status_code == 200
    assert response.json()["transaction_id"] == "TXN_LOOKUP"


@pytest.mark.asyncio
async def test_get_transaction_by_id_not_found(
    transactions_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _session = transactions_client
    response = await client.get("/transactions/TXN_MISSING")
    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found"


@pytest.mark.asyncio
async def test_list_transactions_all(
    transactions_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _session = transactions_client
    await client.post("/transactions", json=_transaction_payload(transaction_id="TXN_A"))
    await client.post("/transactions", json=_transaction_payload(transaction_id="TXN_B"))

    response = await client.get("/transactions")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_transactions_filter_by_store(
    transactions_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _session = transactions_client
    await client.post(
        "/transactions",
        json=_transaction_payload(store_id="STORE_A", transaction_id="TXN_1"),
    )
    await client.post(
        "/transactions",
        json=_transaction_payload(store_id="STORE_B", transaction_id="TXN_2"),
    )

    response = await client.get("/transactions", params={"store_id": "STORE_A"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["store_id"] == "STORE_A"


@pytest.mark.asyncio
async def test_list_transactions_filter_by_date_range(
    transactions_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _session = transactions_client
    base = datetime(2026, 3, 3, 12, 0, tzinfo=UTC)
    await client.post(
        "/transactions",
        json=_transaction_payload(
            transaction_id="TXN_OLD",
            timestamp=base - timedelta(hours=2),
        ),
    )
    await client.post(
        "/transactions",
        json=_transaction_payload(
            transaction_id="TXN_IN_RANGE",
            timestamp=base,
        ),
    )

    response = await client.get(
        "/transactions",
        params={
            "start_time": (base - timedelta(hours=1)).isoformat(),
            "end_time": (base + timedelta(hours=1)).isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["transaction_id"] == "TXN_IN_RANGE"


@pytest.mark.asyncio
async def test_list_transactions_pagination(
    transactions_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _session = transactions_client
    base = datetime(2026, 3, 3, 12, 0, tzinfo=UTC)
    for index in range(3):
        await client.post(
            "/transactions",
            json=_transaction_payload(
                transaction_id=f"TXN_PAG_{index}",
                timestamp=base + timedelta(minutes=index),
            ),
        )

    response = await client.get("/transactions", params={"limit": 1, "offset": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_transaction_response_schema_validation(
    transactions_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _session = transactions_client
    response = await client.post("/transactions", json=_transaction_payload())
    assert response.status_code == 201
    parsed = TransactionRead.model_validate(response.json())
    assert parsed.transaction_id == "TXN_001"
