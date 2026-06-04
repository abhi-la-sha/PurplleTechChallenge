
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ZoneDwellState:
    zone_id: str
    enter_time: float
    last_dwell_emit_time: float


@dataclass
class TrackState:
    visitor_id: str
    is_staff: bool = False
    zone: ZoneDwellState | None = None


class VisitorTracker:


    def __init__(
        self,
        reentry_window_s: float = 60.0,
        reentry_position_threshold: float = 0.25,
    ) -> None:
        self._reentry_window_s = reentry_window_s
        self._reentry_pos_thresh = reentry_position_threshold
        self._track_states: dict[int, TrackState] = {}
        self._visitor_seq: dict[str, int] = {}
        self._recently_exited: list[dict] = []

    def get_or_create(
        self,
        track_id: int,
        entry_position: tuple[float, float] | None = None,
    ) -> tuple[str, bool]:

        if track_id in self._track_states:
            return self._track_states[track_id].visitor_id, False

        is_reentry = False
        matched_id: str | None = None

        if entry_position:
            matched_id = self._find_reentry(entry_position)

        if matched_id:
            visitor_id = matched_id
            is_reentry = True
            logger.debug("Re-entry detected: %s (track %d)", visitor_id, track_id)
        else:
            visitor_id = self._new_visitor_id(track_id)

        self._track_states[track_id] = TrackState(visitor_id=visitor_id)
        if visitor_id not in self._visitor_seq:
            self._visitor_seq[visitor_id] = 0

        return visitor_id, is_reentry

    def get_state(self, track_id: int) -> TrackState | None:
        return self._track_states.get(track_id)

    def next_seq(self, visitor_id: str) -> int:
        seq = self._visitor_seq.get(visitor_id, 0)
        self._visitor_seq[visitor_id] = seq + 1
        return seq

    def mark_exit(
        self,
        track_id: int,
        exit_position: tuple[float, float],
    ) -> None:
        state = self._track_states.get(track_id)
        if not state:
            return
        self._recently_exited.append(
            {
                "visitor_id": state.visitor_id,
                "position": exit_position,
                "exit_time": time.monotonic(),
            }
        )
        self._prune_exits()

    def all_track_ids(self) -> set[int]:
        return set(self._track_states.keys())

    def remove_track(self, track_id: int) -> None:
        self._track_states.pop(track_id, None)

    

    def _new_visitor_id(self, track_id: int) -> str:
        token = hashlib.md5(
            f"{track_id}_{time.monotonic()}".encode()
        ).hexdigest()[:6]
        return f"VIS_{token}"

    def _find_reentry(self, pos: tuple[float, float]) -> str | None:
        now = time.monotonic()
        best: str | None = None
        best_dist = self._reentry_pos_thresh

        for exited in self._recently_exited:
            age = now - exited["exit_time"]
            if age > self._reentry_window_s:
                continue
            ex, ey = exited["position"]
            nx, ny = pos
            dist = ((ex - nx) ** 2 + (ey - ny) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best = exited["visitor_id"]

        return best

    def _prune_exits(self) -> None:
        now = time.monotonic()
        self._recently_exited = [
            v
            for v in self._recently_exited
            if now - v["exit_time"] < self._reentry_window_s
        ]