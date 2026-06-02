
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_returns_service_metadata(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "service": "store-intelligence-api",
        "version": "0.1.0",
    }
