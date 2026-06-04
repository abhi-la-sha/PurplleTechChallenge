
from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import cv2

from cv.config import (
    BATCH_SIZE,
    DATA_DIR,
    EVENT_API_URL,
    MAX_RETRIES,
    OUTPUT_DIR,
    REQUEST_TIMEOUT_S,
    RETRY_DELAY_S,
    REENTRY_POSITION_THRESHOLD,
    REENTRY_WINDOW_S,
    SKIP_FRAMES,
    STORE_MAPPINGS,
    VIDEO_MAPPINGS,
    YOLO_CONFIDENCE,
    YOLO_MODEL,
    ZONE_DWELL_EMIT_INTERVAL_S,
    ZONE_LOST_TRACK_TIMEOUT_S,
    VideoConfig,
)
from cv.detect import PersonTracker
from cv.emit import EventEmitter
from cv.staff import StaffDetector
from cv.tracker import VisitorTracker
from cv.utils import (
    LineCrossingDetector,
    OverlayStats,
    VideoAnnotator,
    bbox_centre,
    bbox_foot_point,
    frame_timestamp,
    normalise_point,
    parse_clip_start,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class VideoResult:
    filename: str
    video_type: str
    frames_processed: int = 0
    persons_detected: int = 0
    unique_visitors: int = 0
    staff_count: int = 0
    events: dict[str, int] = field(default_factory=dict)
    output_path: str = ""
    error: str | None = None

    def add_event(self, event_type: str) -> None:
        self.events[event_type] = self.events.get(event_type, 0) + 1


@dataclass
class StoreResult:
    store_id: str
    videos: list[VideoResult] = field(default_factory=list)

    def total_events(self) -> int:
        return sum(sum(v.events.values()) for v in self.videos)

    def total_visitors(self) -> int:
        return sum(v.unique_visitors for v in self.videos)

    def total_staff(self) -> int:
        return sum(v.staff_count for v in self.videos)



def process_entry_video(
    cap: cv2.VideoCapture,
    config: VideoConfig,
    store_id: str,
    tracker: PersonTracker,
    visitor_tracker: VisitorTracker,
    staff_detector: StaffDetector,
    emitter: EventEmitter,
    annotator: VideoAnnotator,
    fps: float,
    result: VideoResult,
) -> None:
    
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    clip_start = parse_clip_start(config.clip_start)
    line_detector = LineCrossingDetector(
        config.line_y, frame_h, invert=config.invert_crossing
    )
    line_y_px = int(config.line_y * frame_h)
    frame_num = 0
    staff_flags: dict[int, bool] = {}
    unique_visitor_ids: set[str] = set()
    staff_ids: set[str] = set()

    while True:

        for _ in range(SKIP_FRAMES - 1):
            ret = cap.grab()
            if not ret:
                return
            frame_num += 1

        ret, frame = cap.read()
        if not ret:
            break
        frame_num += 1

        ts = frame_timestamp(clip_start, frame_num, SKIP_FRAMES, fps)
        persons = tracker.update(frame)

        track_ids = [p.track_id for p in persons]
        centres = [bbox_centre(p.bbox) for p in persons]
        entered_ids, exited_ids = line_detector.update(track_ids, centres)

        active_events: list[tuple[int, str]] = []

        for person in persons:
            tid = person.track_id
            is_staff = staff_detector.is_staff(frame, person.bbox)
            staff_flags[tid] = is_staff

        for tid in entered_ids:
            person = next((p for p in persons if p.track_id == tid), None)
            if person is None:
                continue
            cx, cy = bbox_centre(person.bbox)
            norm_pos = normalise_point((cx, cy), frame_w, frame_h)
            visitor_id, is_reentry = visitor_tracker.get_or_create(tid, norm_pos)
            is_staff = staff_flags.get(tid, False)
            seq = visitor_tracker.next_seq(visitor_id)

            if is_reentry:
                emitter.emit(
                    "REENTRY", visitor_id, ts,
                    is_staff=is_staff, confidence=person.confidence,
                    extra_meta={"track_id": tid, "session_seq": seq},
                )
                result.add_event("REENTRY")
                active_events.append((tid, "REENTRY"))
            else:
                emitter.emit(
                    "ENTRY", visitor_id, ts,
                    is_staff=is_staff, confidence=person.confidence,
                    extra_meta={"track_id": tid, "session_seq": seq},
                )
                result.add_event("ENTRY")
                active_events.append((tid, "ENTRY"))

            unique_visitor_ids.add(visitor_id)
            if is_staff:
                staff_ids.add(visitor_id)

        for tid in exited_ids:
            person = next((p for p in persons if p.track_id == tid), None)
            if person is None:
                continue
            cx, cy = bbox_centre(person.bbox)
            norm_pos = normalise_point((cx, cy), frame_w, frame_h)
            visitor_id, _ = visitor_tracker.get_or_create(tid)
            is_staff = staff_flags.get(tid, False)
            seq = visitor_tracker.next_seq(visitor_id)
            visitor_tracker.mark_exit(tid, norm_pos)
            emitter.emit(
                "EXIT", visitor_id, ts,
                is_staff=is_staff, confidence=person.confidence,
                extra_meta={"track_id": tid, "session_seq": seq},
            )
            result.add_event("EXIT")
            active_events.append((tid, "EXIT"))

        result.frames_processed += 1
        result.persons_detected += len(persons)
        result.unique_visitors = len(unique_visitor_ids - staff_ids)
        result.staff_count = len(staff_ids)

        stats = OverlayStats(
            store_id=store_id,
            source_video=config.filename,
            active_tracks=len(persons),
            visitors=result.unique_visitors,
            staff=result.staff_count,
            events=sum(result.events.values()),
        )
        annotator.write(
            frame, persons, staff_flags, active_events, stats,
            line_y_px=line_y_px,
        )


def process_zone_video(
    cap: cv2.VideoCapture,
    config: VideoConfig,
    store_id: str,
    tracker: PersonTracker,
    visitor_tracker: VisitorTracker,
    staff_detector: StaffDetector,
    emitter: EventEmitter,
    annotator: VideoAnnotator,
    fps: float,
    result: VideoResult,
) -> None:
    
    clip_start = parse_clip_start(config.clip_start)
    zone_id = config.zone_id or "ZONE"
    frame_num = 0

    in_zone: dict[int, tuple[float, float]] = {}
    staff_flags: dict[int, bool] = {}
    unique_visitor_ids: set[str] = set()
    staff_ids: set[str] = set()

    while True:
        for _ in range(SKIP_FRAMES - 1):
            ret = cap.grab()
            if not ret:
                return
            frame_num += 1

        ret, frame = cap.read()
        if not ret:
            break
        frame_num += 1

        ts = frame_timestamp(clip_start, frame_num, SKIP_FRAMES, fps)
        now_epoch = ts.timestamp()
        persons = tracker.update(frame)
        active_ids = {p.track_id for p in persons}
        active_events: list[tuple[int, str]] = []

        for person in persons:
            staff_flags[person.track_id] = staff_detector.is_staff(frame, person.bbox)

        
        for tid in list(in_zone.keys()):
            if tid not in active_ids:
                enter_epoch, _ = in_zone.pop(tid)
                state = visitor_tracker.get_state(tid)
                visitor_id = state.visitor_id if state else f"VIS_lost_{tid}"
                is_staff = staff_flags.get(tid, False)
                seq = visitor_tracker.next_seq(visitor_id)
                dwell_ms = int((now_epoch - enter_epoch) * 1000)
                emitter.emit(
                    "ZONE_EXIT", visitor_id, ts,
                    is_staff=is_staff, confidence=1.0,
                    zone_id=zone_id, dwell_ms=dwell_ms,
                    extra_meta={"track_id": tid, "session_seq": seq},
                )
                result.add_event("ZONE_EXIT")

        
        for person in persons:
            tid = person.track_id
            is_staff = staff_flags.get(tid, False)
            visitor_id, _ = visitor_tracker.get_or_create(tid)
            unique_visitor_ids.add(visitor_id)
            if is_staff:
                staff_ids.add(visitor_id)
            state = visitor_tracker.get_state(tid)

            if tid not in in_zone:
                # Zone enter
                in_zone[tid] = (now_epoch, now_epoch)
                seq = visitor_tracker.next_seq(visitor_id)
                emitter.emit(
                    "ZONE_ENTER", visitor_id, ts,
                    is_staff=is_staff, confidence=person.confidence,
                    zone_id=zone_id, dwell_ms=0,
                    extra_meta={"track_id": tid, "session_seq": seq},
                )
                result.add_event("ZONE_ENTER")
                active_events.append((tid, "ZONE_ENTER"))
            else:
                enter_epoch, last_dwell = in_zone[tid]
                since_dwell = now_epoch - last_dwell
                if since_dwell >= ZONE_DWELL_EMIT_INTERVAL_S:
                    dwell_ms = int((now_epoch - enter_epoch) * 1000)
                    seq = visitor_tracker.next_seq(visitor_id)
                    emitter.emit(
                        "ZONE_DWELL", visitor_id, ts,
                        is_staff=is_staff, confidence=person.confidence,
                        zone_id=zone_id, dwell_ms=dwell_ms,
                        extra_meta={"track_id": tid, "session_seq": seq},
                    )
                    result.add_event("ZONE_DWELL")
                    active_events.append((tid, "ZONE_DWELL"))
                    in_zone[tid] = (enter_epoch, now_epoch)

        result.frames_processed += 1
        result.persons_detected += len(persons)
        result.unique_visitors = len(unique_visitor_ids - staff_ids)
        result.staff_count = len(staff_ids)

        stats = OverlayStats(
            store_id=store_id, source_video=config.filename,
            active_tracks=len(persons),
            visitors=result.unique_visitors, staff=result.staff_count,
            events=sum(result.events.values()),
        )
        annotator.write(frame, persons, staff_flags, active_events, stats)


def process_billing_video(
    cap: cv2.VideoCapture,
    config: VideoConfig,
    store_id: str,
    tracker: PersonTracker,
    visitor_tracker: VisitorTracker,
    staff_detector: StaffDetector,
    emitter: EventEmitter,
    annotator: VideoAnnotator,
    fps: float,
    result: VideoResult,
) -> None:
    
    clip_start = parse_clip_start(config.clip_start)
    zone_id = config.zone_id or "BILLING"
    frame_num = 0

    in_queue: dict[int, float] = {}  # track_id -> enter_epoch
    staff_flags: dict[int, bool] = {}
    unique_visitor_ids: set[str] = set()
    staff_ids: set[str] = set()

    while True:
        for _ in range(SKIP_FRAMES - 1):
            ret = cap.grab()
            if not ret:
                return
            frame_num += 1

        ret, frame = cap.read()
        if not ret:
            break
        frame_num += 1

        ts = frame_timestamp(clip_start, frame_num, SKIP_FRAMES, fps)
        now_epoch = ts.timestamp()
        persons = tracker.update(frame)
        active_ids = {p.track_id for p in persons}
        active_events: list[tuple[int, str]] = []

        for person in persons:
            staff_flags[person.track_id] = staff_detector.is_staff(frame, person.bbox)

        current_customer_ids = {
            p.track_id for p in persons if not staff_flags.get(p.track_id, False)
        }
        queue_depth = len(set(in_queue.keys()) & current_customer_ids)

        
        for tid in list(in_queue.keys()):
            if tid not in active_ids:
                enter_epoch = in_queue.pop(tid)
                state = visitor_tracker.get_state(tid)
                visitor_id = state.visitor_id if state else f"VIS_lost_{tid}"
                seq = visitor_tracker.next_seq(visitor_id)
                dwell_ms = int((now_epoch - enter_epoch) * 1000)
                emitter.emit(
                    "BILLING_QUEUE_ABANDON", visitor_id, ts,
                    is_staff=False, confidence=1.0,
                    zone_id=zone_id, dwell_ms=dwell_ms,
                    extra_meta={
                        "track_id": tid,
                        "session_seq": seq,
                        "queue_depth": queue_depth,
                    },
                )
                result.add_event("BILLING_QUEUE_ABANDON")
                active_events.append((tid, "ABANDON"))

        for person in persons:
            tid = person.track_id
            is_staff = staff_flags.get(tid, False)

            if is_staff:
                staff_ids.add(visitor_tracker.get_or_create(tid)[0])
                continue

            visitor_id, _ = visitor_tracker.get_or_create(tid)
            unique_visitor_ids.add(visitor_id)

            if tid not in in_queue:
                in_queue[tid] = now_epoch
                updated_depth = len(in_queue)
                seq = visitor_tracker.next_seq(visitor_id)
                emitter.emit(
                    "BILLING_QUEUE_JOIN", visitor_id, ts,
                    is_staff=False, confidence=person.confidence,
                    zone_id=zone_id, dwell_ms=0,
                    extra_meta={
                        "track_id": tid,
                        "session_seq": seq,
                        "queue_depth": updated_depth,
                        "queue_position": updated_depth,
                    },
                )
                result.add_event("BILLING_QUEUE_JOIN")
                active_events.append((tid, "QUEUE_JOIN"))

        result.frames_processed += 1
        result.persons_detected += len(persons)
        result.unique_visitors = len(unique_visitor_ids)
        result.staff_count = len(staff_ids)

        stats = OverlayStats(
            store_id=store_id, source_video=config.filename,
            active_tracks=len(persons),
            visitors=result.unique_visitors, staff=result.staff_count,
            events=sum(result.events.values()),
        )
        annotator.write(
            frame, persons, staff_flags, active_events, stats,
            show_billing_region=True,
        )



def process_video(
    folder_name: str,
    store_id: str,
    video_config: VideoConfig,
    device: str,
    dry_run: bool,
) -> VideoResult:
    video_path = DATA_DIR / folder_name / video_config.filename
    stem = Path(video_config.filename).stem
    out_path = OUTPUT_DIR / folder_name / f"{stem}_annotated.mp4"
    result = VideoResult(
        filename=video_config.filename,
        video_type=video_config.video_type,
        output_path=str(out_path),
    )

    if not video_path.exists():
        result.error = f"Video not found: {video_path}"
        logger.error(result.error)
        return result

    logger.info(
        "Processing: %s | store=%s | type=%s",
        video_path,
        store_id,
        video_config.video_type,
    )

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        result.error = f"Cannot open: {video_path}"
        logger.error(result.error)
        return result

    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    logger.info(
        "Video: %dx%d @ %.1ffps | %d frames (%.0fs)",
        frame_w, frame_h, fps, total_frames, total_frames / fps,
    )

    person_tracker = PersonTracker(
        model_path=YOLO_MODEL,
        confidence=YOLO_CONFIDENCE,
        device=device,
    )
    visitor_tracker = VisitorTracker(
        reentry_window_s=REENTRY_WINDOW_S,
        reentry_position_threshold=REENTRY_POSITION_THRESHOLD,
    )
    staff_detector = StaffDetector(store_id)
    emitter = EventEmitter(
        api_url=EVENT_API_URL,
        store_id=store_id,
        camera_id=video_config.camera_id,
        source_video=video_config.filename,
        batch_size=BATCH_SIZE,
        max_retries=MAX_RETRIES,
        retry_delay_s=RETRY_DELAY_S,
        timeout_s=REQUEST_TIMEOUT_S,
        dry_run=dry_run,
    )
    annotator = VideoAnnotator(out_path, frame_w, frame_h, fps / SKIP_FRAMES)

    try:
        if video_config.video_type == "entry":
            process_entry_video(
                cap, video_config, store_id, person_tracker, visitor_tracker,
                staff_detector, emitter, annotator, fps, result,
            )
        elif video_config.video_type == "zone":
            process_zone_video(
                cap, video_config, store_id, person_tracker, visitor_tracker,
                staff_detector, emitter, annotator, fps, result,
            )
        elif video_config.video_type == "billing":
            process_billing_video(
                cap, video_config, store_id, person_tracker, visitor_tracker,
                staff_detector, emitter, annotator, fps, result,
            )
    except Exception as exc:
        logger.exception("Error processing %s: %s", video_config.filename, exc)
        result.error = str(exc)
    finally:
        cap.release()
        annotator.release()
        emitter.flush()
        result.events["_emitted"] = emitter.total_emitted

    return result


def run_all(
    device: str = "cpu",
    dry_run: bool = False,
    store_filter: str | None = None,
) -> list[StoreResult]:
    store_results: list[StoreResult] = []

    for folder_name, store_id in STORE_MAPPINGS.items():
        if store_filter and store_id != store_filter:
            continue

        if store_id not in VIDEO_MAPPINGS:
            logger.warning("No video mappings for %s — skipping", store_id)
            continue

        store_result = StoreResult(store_id=store_id)
        video_configs = VIDEO_MAPPINGS[store_id]

        logger.info("━━━ Processing store: %s (%s) ━━━", store_id, folder_name)

        for vc in video_configs:
            t0 = time.time()
            vr = process_video(folder_name, store_id, vc, device, dry_run)
            elapsed = time.time() - t0
            logger.info(
                "Done: %s in %.1fs | events=%d",
                vc.filename, elapsed, sum(vr.events.values()),
            )
            store_result.videos.append(vr)

        store_results.append(store_result)

    return store_results


def print_summary(store_results: list[StoreResult]) -> None:
    print("\n" + "=" * 60)
    print("  PROCESSING SUMMARY")
    print("=" * 60)

    for sr in store_results:
        print(f"\n  {sr.store_id}")
        print(f"  {'─' * 40}")

        all_event_types = [
            "ENTRY", "EXIT", "REENTRY",
            "ZONE_ENTER", "ZONE_EXIT", "ZONE_DWELL",
            "BILLING_QUEUE_JOIN", "BILLING_QUEUE_ABANDON",
        ]
        totals: dict[str, int] = {}

        for vr in sr.videos:
            status = "✓" if vr.error is None else "✗"
            print(f"\n  {status}  {vr.filename}  [{vr.video_type}]")
            if vr.error:
                print(f"     ERROR: {vr.error}")
                continue
            print(f"     Frames processed : {vr.frames_processed}")
            print(f"     Persons detected : {vr.persons_detected}")
            print(f"     Unique visitors  : {vr.unique_visitors}")
            print(f"     Staff detected   : {vr.staff_count}")
            for et in all_event_types:
                count = vr.events.get(et, 0)
                if count > 0:
                    print(f"     {et:30s}: {count}")
                    totals[et] = totals.get(et, 0) + count
            if vr.output_path:
                print(f"     Output: {vr.output_path}")

        print(f"\n  Store totals:")
        print(f"     Unique visitors : {sr.total_visitors()}")
        print(f"     Staff           : {sr.total_staff()}")
        print(f"     Total events    : {sr.total_events()}")
        for et, count in totals.items():
            print(f"     {et:30s}: {count}")

    print("\n" + "=" * 60)



def main() -> None:
    parser = argparse.ArgumentParser(
        description="Purplle Store Intelligence — CV Batch Runner"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print events to log instead of POSTing to API",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        choices=["cpu", "cuda", "mps"],
        help="Inference device",
    )
    parser.add_argument(
        "--store",
        default=None,
        help="Process one store only e.g. STORE_001",
    )
    args = parser.parse_args()

    logger.info(
        "Starting batch runner | device=%s dry_run=%s store_filter=%s",
        args.device,
        args.dry_run,
        args.store,
    )

    results = run_all(
        device=args.device,
        dry_run=args.dry_run,
        store_filter=args.store,
    )
    print_summary(results)


if __name__ == "__main__":
    main()