
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)


@dataclass
class CVEvent:

    event_id: str
    store_id: str
    camera_id: str
    visitor_id: str
    event_type: str
    timestamp: str
    zone_id: str | None = None
    dwell_ms: int | None = None
    is_staff: bool = False
    confidence: float = 1.0
    metadata: dict[str, Any] | None = None


class EventEmitter:
    def __init__(
        self,
        api_url: str,
        store_id: str,
        camera_id: str,
        source_video: str,
        batch_size: int = 50,
        max_retries: int = 3,
        retry_delay_s: float = 2.0,
        timeout_s: float = 15.0,
        dry_run: bool = False,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        self._store_id = store_id
        self._camera_id = camera_id
        self._source_video = source_video
        self._batch_size = batch_size
        self._max_retries = max_retries
        self._retry_delay_s = retry_delay_s
        self._timeout_s = timeout_s
        self._dry_run = dry_run
        self._buffer: list[dict] = []
        self._total_emitted = 0
        self._total_errors = 0

    def emit(
        self,
        event_type: str,
        visitor_id: str,
        timestamp: datetime,
        is_staff: bool = False,
        confidence: float = 1.0,
        zone_id: str | None = None,
        dwell_ms: int | None = None,
        extra_meta: dict[str, Any] | None = None,
    ) -> CVEvent:
        
        meta: dict[str, Any] = {
            "source_video": self._source_video,
            "pipeline": "cv",
            "is_staff": is_staff,
        }
        if extra_meta:
            meta.update(extra_meta)

        event = CVEvent(
            event_id=str(uuid.uuid4()),
            store_id=self._store_id,
            camera_id=self._camera_id,
            visitor_id=visitor_id,
            event_type=event_type,
            timestamp=timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            zone_id=zone_id,
            dwell_ms=dwell_ms,
            is_staff=is_staff,
            confidence=round(confidence, 4),
            metadata=meta,
        )
        self._buffer.append(asdict(event))

        if len(self._buffer) >= self._batch_size:
            self._flush()

        return event

    def flush(self) -> None:
        
        self._flush()
        logger.info(
            "EventEmitter flush complete — total_emitted=%d total_errors=%d",
            self._total_emitted,
            self._total_errors,
        )

    @property
    def total_emitted(self) -> int:
        return self._total_emitted


    def _flush(self) -> None:
        if not self._buffer:
            return

        if self._dry_run:
            for e in self._buffer:
                logger.info(
                    "[DRY RUN] %s | visitor=%s | staff=%s | %s",
                    e["event_type"],
                    e["visitor_id"],
                    e["is_staff"],
                    e["timestamp"],
                )
            self._total_emitted += len(self._buffer)
            self._buffer.clear()
            return

        payload = {"events": self._buffer}
        batch_count = len(self._buffer)

        for attempt in range(1, self._max_retries + 1):
            try:
                resp = requests.post(
                    f"{self._api_url}/events/ingest",
                    json=payload,
                    timeout=self._timeout_s,
                )
                resp.raise_for_status()
                result = resp.json()
                ingested = result.get("ingested", 0)
                duplicates = result.get("duplicates", 0)
                errors = result.get("errors", [])
                self._total_emitted += ingested
                if errors:
                    self._total_errors += len(errors)
                    logger.warning(
                        "Ingest partial errors: %d errors in batch of %d",
                        len(errors),
                        batch_count,
                    )
                logger.debug(
                    "Batch ingested: ingested=%d duplicates=%d errors=%d",
                    ingested,
                    duplicates,
                    len(errors),
                )
                self._buffer.clear()
                return

            except requests.RequestException as exc:
                logger.warning(
                    "Ingest attempt %d/%d failed: %s",
                    attempt,
                    self._max_retries,
                    exc,
                )
                if attempt < self._max_retries:
                    time.sleep(self._retry_delay_s * attempt)

        logger.error(
            "All %d retries failed — dropping batch of %d events",
            self._max_retries,
            batch_count,
        )
        self._total_errors += batch_count
        self._buffer.clear()