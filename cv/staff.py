
from __future__ import annotations

import logging

import cv2
import numpy as np

from cv.config import STAFF_COLOR_CONFIG, StaffColorConfig

logger = logging.getLogger(__name__)


class StaffDetector:
    def __init__(self, store_id: str) -> None:
        if store_id not in STAFF_COLOR_CONFIG:
            raise ValueError(f"No staff config for store: {store_id}")
        self._cfg: StaffColorConfig = STAFF_COLOR_CONFIG[store_id]
        logger.info(
            "StaffDetector: store=%s method=%s colour=%s",
            store_id,
            self._cfg.method,
            self._cfg.color_name,
        )

    def is_staff(
        self,
        frame: np.ndarray,
        bbox: tuple[float, float, float, float],
    ) -> bool:
        
        torso = self._extract_torso(frame, bbox)
        if torso is None:
            return False

        if self._cfg.method == "dark":
            return self._detect_dark(torso)
        elif self._cfg.method == "hue":
            return self._detect_hue(torso)
        return False

    
    def _extract_torso(
        self,
        frame: np.ndarray,
        bbox: tuple[float, float, float, float],
    ) -> np.ndarray | None:
        x1, y1, x2, y2 = map(int, bbox)
        h, w = y2 - y1, x2 - x1

        if h < 30 or w < 10:
            return None

        ty1 = y1 + int(h * 0.30)
        ty2 = y1 + int(h * 0.70)

        fh, fw = frame.shape[:2]
        ty1 = max(0, min(ty1, fh - 1))
        ty2 = max(0, min(ty2, fh))
        x1 = max(0, min(x1, fw - 1))
        x2 = max(0, min(x2, fw))

        torso = frame[ty1:ty2, x1:x2]
        return torso if torso.size > 0 else None

    def _detect_dark(self, torso: np.ndarray) -> bool:

        hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]
        dark_pixels = int((v_channel < self._cfg.dark_v_thresh).sum())
        fraction = dark_pixels / v_channel.size
        return fraction >= self._cfg.dark_fraction

    def _detect_hue(self, torso: np.ndarray) -> bool:
        
        hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)
        h = hsv[:, :, 0]
        s = hsv[:, :, 1]
        v = hsv[:, :, 2]

      
        valid_mask = (s >= self._cfg.sat_min) & (v >= self._cfg.val_min)
        valid_count = int(valid_mask.sum())

        if valid_count == 0:
            return False

        hue_mask = (h >= self._cfg.hue_min) & (h <= self._cfg.hue_max) & valid_mask
        fraction = int(hue_mask.sum()) / valid_count
        return fraction >= self._cfg.hue_fraction