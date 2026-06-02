
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.main import create_app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    application = create_app()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 1
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield mock_session

    application.dependency_overrides[get_async_session] = override_session

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client

    application.dependency_overrides.clear()
