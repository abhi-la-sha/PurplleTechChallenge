
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import cv2
import numpy as np

from cv.config import (
    COLOUR_BILLING_REGION,
    COLOUR_CUSTOMER,
    COLOUR_ENTRY_LINE,
    COLOUR_STAFF,
    COLOUR_TEXT_BG,
    COLOUR_TEXT_FG,
)

logger = logging.getLogger(__name__)




def parse_clip_start(iso_str: str | None) -> datetime:
    if iso_str:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def frame_timestamp(
    clip_start: datetime,
    frame_num: int,
    skip: int,
    fps: float,
) -> datetime:
    
    elapsed_s = (frame_num * skip) / fps
    return clip_start + timedelta(seconds=elapsed_s)


def normalise_point(
    point: tuple[float, float],
    frame_w: int,
    frame_h: int,
) -> tuple[float, float]:
    return point[0] / frame_w, point[1] / frame_h


def bbox_foot_point(
    bbox: tuple[float, float, float, float],
) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2.0, y2


def bbox_centre(
    bbox: tuple[float, float, float, float],
) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0



class LineCrossingDetector:
    def __init__(
        self,
        line_y: float,
        frame_height: int,
        invert: bool = False,
    ) -> None:
        self.line_y_px: int = int(line_y * frame_height)
        self.invert = invert
        self._last_y: dict[int, float] = {}
        self._emitted_this_cross: set[int] = set()

    def update(
        self,
        track_ids: list[int],
        centres: list[tuple[float, float]],
    ) -> tuple[list[int], list[int]]:
        
        entered: list[int] = []
        exited: list[int] = []
        current_ids = set(track_ids)

        for tid, (cx, cy) in zip(track_ids, centres):
            if tid in self._last_y:
                prev_y = self._last_y[tid]
                crossed_down = prev_y < self.line_y_px <= cy
                crossed_up = prev_y > self.line_y_px >= cy

                if tid not in self._emitted_this_cross:
                    if not self.invert:
                        if crossed_down:
                            entered.append(tid)
                            self._emitted_this_cross.add(tid)
                        elif crossed_up:
                            exited.append(tid)
                            self._emitted_this_cross.add(tid)
                    else:
                        if crossed_up:
                            entered.append(tid)
                            self._emitted_this_cross.add(tid)
                        elif crossed_down:
                            exited.append(tid)
                            self._emitted_this_cross.add(tid)
                else:
                
                    if abs(cy - self.line_y_px) > 30:
                        self._emitted_this_cross.discard(tid)

            self._last_y[tid] = cy

        
        for tid in list(self._last_y.keys()):
            if tid not in current_ids:
                del self._last_y[tid]
                self._emitted_this_cross.discard(tid)

        return entered, exited



@dataclass
class OverlayStats:
    store_id: str
    source_video: str
    active_tracks: int = 0
    visitors: int = 0
    staff: int = 0
    events: int = 0


class VideoAnnotator:
    def __init__(
        self,
        output_path: Path,
        frame_width: int,
        frame_height: int,
        fps: float,
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore[attr-defined]
        self._writer = cv2.VideoWriter(
            str(output_path),
            fourcc,
            fps,
            (frame_width, frame_height),
        )
        if not self._writer.isOpened():
            raise RuntimeError(f"Cannot open VideoWriter: {output_path}")
        self._out_path = output_path
        logger.info("VideoAnnotator writing to: %s", output_path)

    def write(
        self,
        frame: np.ndarray,
        tracked_persons: list,  # list[TrackedPerson]
        staff_flags: dict[int, bool],
        active_events: list[tuple[int, str]],  # [(track_id, event_label)]
        stats: OverlayStats,
        line_y_px: int | None = None,
        show_billing_region: bool = False,
    ) -> None:
        annotated = frame.copy()

        
        if line_y_px is not None:
            h, w = annotated.shape[:2]
            cv2.line(
                annotated,
                (0, line_y_px),
                (w, line_y_px),
                COLOUR_ENTRY_LINE,
                2,
            )
            self._put_text(annotated, "ENTRY THRESHOLD", (5, line_y_px - 8), scale=0.5)

        
        if show_billing_region:
            h, w = annotated.shape[:2]
            overlay = annotated.copy()
            cv2.rectangle(overlay, (0, 0), (w, h), COLOUR_BILLING_REGION, -1)
            cv2.addWeighted(overlay, 0.08, annotated, 0.92, 0, annotated)
            cv2.rectangle(annotated, (0, 0), (w, h), COLOUR_BILLING_REGION, 3)
            self._put_text(annotated, "BILLING ZONE", (5, 25), scale=0.6)

        
        event_map: dict[int, list[str]] = {}
        for tid, label in active_events:
            event_map.setdefault(tid, []).append(label)

        
        for person in tracked_persons:
            x1, y1, x2, y2 = map(int, person.bbox)
            is_staff = staff_flags.get(person.track_id, False)
            colour = COLOUR_STAFF if is_staff else COLOUR_CUSTOMER
            label = "STAFF" if is_staff else "CUSTOMER"

            
            cv2.rectangle(annotated, (x1, y1), (x2, y2), colour, 2)

           
            header = f"ID:{person.track_id}  {person.confidence:.2f}"
            self._put_text(annotated, header, (x1, y1 - 20), colour=colour, scale=0.5)

            
            self._put_text(annotated, label, (x1, y1 - 6), colour=colour, scale=0.45)

            
            if person.track_id in event_map:
                for j, ev_label in enumerate(event_map[person.track_id]):
                    self._put_text(
                        annotated,
                        ev_label,
                        (x1, y2 + 16 + j * 18),
                        colour=(0, 255, 255),
                        scale=0.5,
                    )

        
        self._draw_stats(annotated, stats)

        self._writer.write(annotated)

    def release(self) -> None:
        self._writer.release()
        logger.info("VideoAnnotator released: %s", self._out_path)

 

    def _put_text(
        self,
        img: np.ndarray,
        text: str,
        pos: tuple[int, int],
        colour: tuple[int, int, int] = COLOUR_TEXT_FG,
        scale: float = 0.55,
        thickness: int = 1,
    ) -> None:
        x, y = pos
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
        cv2.rectangle(img, (x - 1, y - th - 3), (x + tw + 1, y + 3), COLOUR_TEXT_BG, -1)
        cv2.putText(img, text, (x, y), font, scale, colour, thickness, cv2.LINE_AA)

    def _draw_stats(self, img: np.ndarray, stats: OverlayStats) -> None:
        h, w = img.shape[:2]
        lines = [
            f"{stats.store_id}  |  {stats.source_video}",
            f"Active Tracks: {stats.active_tracks}",
            f"Visitors: {stats.visitors}   Staff: {stats.staff}",
            f"Events Emitted: {stats.events}",
        ]
        line_h = 20
        panel_h = len(lines) * line_h + 10
        y0 = h - panel_h - 5
        cv2.rectangle(img, (0, y0), (300, h - 5), COLOUR_TEXT_BG, -1)
        for i, line in enumerate(lines):
            cv2.putText(
                img,
                line,
                (5, y0 + 16 + i * line_h),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                COLOUR_TEXT_FG,
                1,
                cv2.LINE_AA,
            )