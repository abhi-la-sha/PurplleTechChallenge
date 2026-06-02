
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from app.db.base import Base
from app.db.session import get_async_session
from app.main import create_app
from app.models import Camera, Event, Transaction, VisitorSession, Zone  # noqa: F401
from app.models.visitor_session import VisitorSession
from app.models.transaction import Transaction
from app.repositories.metrics import MetricsRepository
from app.schemas.metrics import MetricsResponse
from app.services.metrics import MetricsService


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(_type: JSONB, compiler: object, **kwargs: object) -> str:
    return "JSON"


@pytest.fixture
async def metrics_client() -> AsyncIterator[tuple[AsyncClient, AsyncSession]]:
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


async def _seed_visitor_sessions(session: AsyncSession) -> None:
    session.add_all(
        [
            VisitorSession(
                visitor_id="v1",
                entry_time=datetime.now(UTC),
                session_duration_seconds=100,
                converted=True,
            ),
            VisitorSession(
                visitor_id="v2",
                entry_time=datetime.now(UTC),
                session_duration_seconds=200,
                converted=True,
            ),
            VisitorSession(
                visitor_id="v3",
                entry_time=datetime.now(UTC),
                session_duration_seconds=300,
                converted=False,
            ),
            VisitorSession(
                visitor_id="v4",
                entry_time=datetime.now(UTC),
                session_duration_seconds=None,
                converted=False,
            ),
        ]
    )
    await session.flush()


async def _seed_transactions(session: AsyncSession) -> None:
    session.add_all(
        [
            Transaction(
                transaction_id="TX-1",
                transaction_timestamp=datetime.now(UTC),
                basket_value=Decimal("100.00"),
            ),
            Transaction(
                transaction_id="TX-2",
                transaction_timestamp=datetime.now(UTC),
                basket_value=Decimal("200.00"),
            ),
            Transaction(
                transaction_id="TX-3",
                transaction_timestamp=datetime.now(UTC),
                basket_value=Decimal("300.00"),
            ),
        ]
    )
    await session.flush()


@pytest.mark.asyncio
async def test_metrics_empty_database(metrics_client: tuple[AsyncClient, AsyncSession]) -> None:
    client, _session = metrics_client
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert response.json() == {
        "total_visitors": 0,
        "converted_visitors": 0,
        "conversion_rate": 0.0,
        "average_dwell_time_seconds": 0.0,
        "average_basket_value": 0.0,
    }


@pytest.mark.asyncio
async def test_metrics_total_visitors(metrics_client: tuple[AsyncClient, AsyncSession]) -> None:
    client, session = metrics_client
    await _seed_visitor_sessions(session)
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert response.json()["total_visitors"] == 4


@pytest.mark.asyncio
async def test_metrics_converted_visitors(
    metrics_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, session = metrics_client
    await _seed_visitor_sessions(session)
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert response.json()["converted_visitors"] == 2


@pytest.mark.asyncio
async def test_metrics_conversion_rate(metrics_client: tuple[AsyncClient, AsyncSession]) -> None:
    client, session = metrics_client
    await _seed_visitor_sessions(session)
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert response.json()["conversion_rate"] == 50.0


@pytest.mark.asyncio
async def test_metrics_average_dwell_time(
    metrics_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, session = metrics_client
    await _seed_visitor_sessions(session)
    response = await client.get("/metrics")
    assert response.status_code == 200
    # AVG(100, 200, 300) = 200.0; NULL session excluded
    assert response.json()["average_dwell_time_seconds"] == 200.0


@pytest.mark.asyncio
async def test_metrics_average_basket_value(
    metrics_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, session = metrics_client
    await _seed_transactions(session)
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert response.json()["average_basket_value"] == 200.0


@pytest.mark.asyncio
async def test_metrics_response_schema(metrics_client: tuple[AsyncClient, AsyncSession]) -> None:
    client, session = metrics_client
    await _seed_visitor_sessions(session)
    await _seed_transactions(session)
    response = await client.get("/metrics")
    assert response.status_code == 200
    parsed = MetricsResponse.model_validate(response.json())
    assert parsed.total_visitors == 4
    assert parsed.converted_visitors == 2


@pytest.mark.asyncio
async def test_metrics_service_full_calculation(
    metrics_client: tuple[AsyncClient, AsyncSession],
) -> None:
    _client, session = metrics_client
    await _seed_visitor_sessions(session)
    await _seed_transactions(session)

    service = MetricsService(MetricsRepository(session))
    metrics = await service.get_metrics()

    assert metrics.total_visitors == 4
    assert metrics.converted_visitors == 2
    assert metrics.conversion_rate == 50.0
    assert metrics.average_dwell_time_seconds == 200.0
    assert metrics.average_basket_value == 200.0


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/heatmap", "/funnel", "/anomalies"])
async def test_future_analytics_placeholders_return_501(
    metrics_client: tuple[AsyncClient, AsyncSession],
    path: str,
) -> None:
    client, _session = metrics_client
    response = await client.get(path)
    assert response.status_code == 501
    assert response.json()["detail"] == "Not Implemented"
