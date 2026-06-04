
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

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
    zone: Optional[ZoneDwellState] = None
    embedding: Optional[np.ndarray] = None


class VisitorTracker:


    def __init__(
        self,
        reentry_window_s: float = 60.0,
        reentry_position_threshold: float = 0.25,
        embedding_threshold: float = 0.85,
    ) -> None:
        self._reentry_window_s = reentry_window_s
        self._reentry_pos_thresh = reentry_position_threshold
        self._embedding_threshold = embedding_threshold
        self._track_states: dict[int, TrackState] = {}
        self._visitor_seq: dict[str, int] = {}
        self._recently_exited: list[dict] = []
        self._embedding_memory: dict[str, np.ndarray] = {}

    def get_or_create(
        self,
        track_id: int,
        entry_position: tuple[float, float] | None = None,
        embedding: np.ndarray | None = None,
    ) -> tuple[str, bool]:

        # If track already exists, reuse it
        if track_id in self._track_states:
            state = self._track_states[track_id]

            # update embedding if new one is available
            if embedding is not None:
                state.embedding = embedding

            return state.visitor_id, False

        is_reentry = False
        matched_id: str | None = None

        # -----------------------------
        # 1. Try Re-entry logic first (position-based)
        # -----------------------------
        if entry_position:
            matched_id = self._find_reentry(entry_position)

        # -----------------------------
        # 2. ReID-lite matching (embedding-based)
        # -----------------------------
        if matched_id is None and embedding is not None:
            matched_id = self._find_by_embedding(embedding)

            if matched_id:
                is_reentry = True
                logger.debug("ReID match found: %s (track %d)", matched_id, track_id)

        # -----------------------------
        # 3. Assign identity
        # -----------------------------
        if matched_id:
            visitor_id = matched_id
        else:
            visitor_id = self._new_visitor_id(track_id)
            if embedding is not None:
                self._embedding_memory[visitor_id] = embedding

        # -----------------------------
        # Save track state
        # -----------------------------
        self._track_states[track_id] = TrackState(
            visitor_id=visitor_id,
            embedding=embedding
        )

        if visitor_id not in self._visitor_seq:
            self._visitor_seq[visitor_id] = 0

        return visitor_id, is_reentry

    # -----------------------------
    # ReID matching (NEW CORE LOGIC)
    # -----------------------------
    def _find_by_embedding(self, embedding: np.ndarray) -> Optional[str]:

        best_id = None
        best_score = 0.0

        for vid, stored_emb in self._embedding_memory.items():
            score = self._cosine_sim(embedding, stored_emb)

            if score > best_score:
                best_score = score
                best_id = vid

        if best_score >= self._embedding_threshold:
            return best_id

        return None

    def _cosine_sim(self, a: np.ndarray, b: np.ndarray) -> float:
        if a is None or b is None:
            return 0.0

        a = a / (np.linalg.norm(a) + 1e-6)
        b = b / (np.linalg.norm(b) + 1e-6)

        return float(np.dot(a, b))

    # -----------------------------
    # Existing methods (unchanged)
    # -----------------------------
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

    # -----------------------------
    # Old ID generation
    # -----------------------------
    def _new_visitor_id(self, track_id: int) -> str:
        token = hashlib.md5(
            f"{track_id}_{time.monotonic()}".encode()
        ).hexdigest()[:6]
        return f"VIS_{token}"

    # -----------------------------
    # Re-entry (position-based fallback)
    # -----------------------------
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