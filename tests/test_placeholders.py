
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    ["/events", "/metrics", "/funnel", "/anomalies", "/heatmap"],
)
async def test_placeholder_returns_501(client: AsyncClient, path: str) -> None:
    response = await client.get(path)
    assert response.status_code == 501
    assert response.json()["detail"] == "Not Implemented"
