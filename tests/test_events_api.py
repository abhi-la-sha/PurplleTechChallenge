
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_event_service
from app.main import create_app
from app.models.enums import EventType
from app.schemas.event import (
    EventBulkCreateRequest,
    EventCreate,
    EventListResponse,
    EventRead,
    EventStatsResponse,
)


class InMemoryEventService:
    
    def __init__(self) -> None:
        self._items: list[EventRead] = []

    async def create_event(self, payload: EventCreate) -> EventRead:
        item = EventRead(
            id=uuid.uuid4(),
            created_at=datetime.now(UTC),
            **payload.model_dump(),
        )
        self._items.append(item)
        return item

    async def create_bulk(self, payload: EventBulkCreateRequest) -> int:
        for event in payload.events:
            await self.create_event(event)
        return len(payload.events)

    async def get_event(self, event_id: uuid.UUID) -> EventRead:
        for item in self._items:
            if item.id == event_id:
                return item
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    async def list_events(
        self,
        *,
        visitor_id: str | None = None,
        event_type: EventType | None = None,
        camera_id: uuid.UUID | None = None,
        zone_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> EventListResponse:
        items = list(self._items)
        if visitor_id is not None:
            items = [item for item in items if item.visitor_id == visitor_id]
        if event_type is not None:
            items = [item for item in items if item.event_type == event_type]
        if camera_id is not None:
            items = [item for item in items if item.camera_id == camera_id]
        if zone_id is not None:
            items = [item for item in items if item.zone_id == zone_id]
        if session_id is not None:
            items = [item for item in items if item.session_id == session_id]

        items.sort(key=lambda event: event.timestamp, reverse=True)
        total = len(items)
        page = items[offset : offset + limit]
        return EventListResponse(items=page, total=total, limit=limit, offset=offset)

    async def get_stats(self) -> EventStatsResponse:
        return EventStatsResponse(total_events=len(self._items))


@pytest.fixture
async def event_client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    service = InMemoryEventService()

    def _override_event_service() -> InMemoryEventService:
        return service

    app.dependency_overrides[get_event_service] = _override_event_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _event_payload(
    *,
    visitor_id: str = "visitor_001",
    event_type: str = "ENTRY",
    timestamp: datetime | None = None,
    confidence: float | None = 0.91,
) -> dict[str, object]:
    event_time = timestamp or datetime.now(UTC)
    return {
        "visitor_id": visitor_id,
        "event_type": event_type,
        "timestamp": event_time.isoformat(),
        "camera_id": None,
        "zone_id": None,
        "session_id": None,
        "confidence": confidence,
        "metadata_json": {"source": "manual_test"},
    }


@pytest.mark.asyncio
async def test_post_events_success(event_client: AsyncClient) -> None:
    response = await event_client.post("/events", json=_event_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["visitor_id"] == "visitor_001"
    assert data["event_type"] == "ENTRY"
    assert "id" in data


@pytest.mark.asyncio
async def test_post_events_invalid_enum(event_client: AsyncClient) -> None:
    response = await event_client.post(
        "/events",
        json=_event_payload(event_type="NOT_A_REAL_EVENT"),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_events_invalid_confidence(event_client: AsyncClient) -> None:
    response = await event_client.post("/events", json=_event_payload(confidence=1.5))
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_events_bulk_success(event_client: AsyncClient) -> None:
    payload = {
        "events": [
            _event_payload(visitor_id="v1", event_type="ENTRY"),
            _event_payload(visitor_id="v2", event_type="EXIT"),
            _event_payload(visitor_id="v3", event_type="ZONE_ENTER"),
        ]
    }
    response = await event_client.post("/events/bulk", json=payload)
    assert response.status_code == 200
    assert response.json() == {"created_count": 3}


@pytest.mark.asyncio
async def test_get_event_by_id(event_client: AsyncClient) -> None:
    created = await event_client.post("/events", json=_event_payload(visitor_id="visitor_lookup"))
    event_id = created.json()["id"]
    response = await event_client.get(f"/events/{event_id}")
    assert response.status_code == 200
    assert response.json()["visitor_id"] == "visitor_lookup"


@pytest.mark.asyncio
async def test_get_event_by_id_not_found(event_client: AsyncClient) -> None:
    response = await event_client.get(f"/events/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"


@pytest.mark.asyncio
async def test_get_events_list(event_client: AsyncClient) -> None:
    await event_client.post("/events", json=_event_payload(visitor_id="list_a"))
    await event_client.post("/events", json=_event_payload(visitor_id="list_b"))
    response = await event_client.get("/events")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_get_events_filtering(event_client: AsyncClient) -> None:
    await event_client.post("/events", json=_event_payload(visitor_id="filtered", event_type="ENTRY"))
    await event_client.post("/events", json=_event_payload(visitor_id="filtered", event_type="EXIT"))
    await event_client.post("/events", json=_event_payload(visitor_id="other", event_type="ENTRY"))

    response = await event_client.get("/events", params={"visitor_id": "filtered", "event_type": "ENTRY"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["visitor_id"] == "filtered"
    assert data["items"][0]["event_type"] == "ENTRY"


@pytest.mark.asyncio
async def test_get_events_pagination(event_client: AsyncClient) -> None:
    base = datetime.now(UTC)
    for i in range(5):
        await event_client.post(
            "/events",
            json=_event_payload(
                visitor_id=f"pag_{i}",
                timestamp=base + timedelta(seconds=i),
            ),
        )
    response = await event_client.get("/events", params={"limit": 2, "offset": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 2
    assert data["offset"] == 1
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_events_stats(event_client: AsyncClient) -> None:
    await event_client.post("/events", json=_event_payload(visitor_id="stats_1"))
    await event_client.post("/events", json=_event_payload(visitor_id="stats_2"))
    response = await event_client.get("/events/stats")
    assert response.status_code == 200
    assert response.json()["total_events"] >= 2
