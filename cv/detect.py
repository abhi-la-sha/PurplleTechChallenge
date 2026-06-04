from __future__ import annotations
import cv2
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
    embedding: np.ndarray | None = None

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

    # def _get_person_crop(self, frame, bbox):
    #     x1, y1, x2, y2 = map(int, bbox)
    #     crop = frame[y1:y2, x1:x2]
    #     return crop

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
            embedding = self._get_embedding(frame, (x1, y1, x2, y2))
            persons.append(
                TrackedPerson(
                    track_id=int(track_id),
                    bbox=(float(x1), float(y1), float(x2), float(y2)),
                    confidence=conf,
                    embedding=embedding,
                )
            )
        return persons

    def _get_embedding(self, frame: np.ndarray, bbox):

        x1, y1, x2, y2 = map(int, bbox)

        # crop safety check
        if x2 <= x1 or y2 <= y1:
            return None

        crop = frame[y1:y2, x1:x2]

        if crop.size == 0:
            return None

        try:
            # resize to fixed shape for consistency
            crop = cv2.resize(crop, (32, 64))

            # grayscale reduces noise + makes embedding stable
            crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

            # flatten → lightweight appearance signature
            embedding = crop.flatten().astype(np.float32)

            # normalize (important for cosine similarity later)
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            return embedding

        except Exception as e:
            logger.debug("Embedding failed: %s", e)
            return None

    def reset(self) -> None:
        
        self._tracker = sv.ByteTrack()