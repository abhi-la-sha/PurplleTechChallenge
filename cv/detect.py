
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import supervision as sv
from ultralytics import YOLO

logger = logging.getLogger(__name__)


@dataclass
class TrackedPerson:
    track_id: int
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2
    confidence: float


class PersonTracker:

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        confidence: float = 0.35,
        device: str = "cpu",
        person_class_id: int = 0,
    ) -> None:
        logger.info("Loading YOLO model: %s on %s", model_path, device)
        self._model = YOLO(model_path)
        self._model.to(device)
        self._confidence = confidence
        self._person_class = person_class_id
        self._tracker = sv.ByteTrack()

    def update(self, frame: np.ndarray) -> list[TrackedPerson]:
        
        results = self._model(
            frame,
            classes=[self._person_class],
            conf=self._confidence,
            verbose=False,
        )[0]

        detections = sv.Detections.from_ultralytics(results)

        if len(detections) == 0:
            return []

        detections = self._tracker.update_with_detections(detections)

        if detections.tracker_id is None or len(detections.tracker_id) == 0:
            return []

        persons: list[TrackedPerson] = []
        for i, track_id in enumerate(detections.tracker_id):
            x1, y1, x2, y2 = detections.xyxy[i]
            conf = (
                float(detections.confidence[i])
                if detections.confidence is not None
                else 1.0
            )
            persons.append(
                TrackedPerson(
                    track_id=int(track_id),
                    bbox=(float(x1), float(y1), float(x2), float(y2)),
                    confidence=conf,
                )
            )
        return persons

    def reset(self) -> None:
        
        self._tracker = sv.ByteTrack()