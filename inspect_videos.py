#!/usr/bin/env python3
"""Lightweight video inspection: metadata to stdout, middle frame to analysis_frames/."""

from pathlib import Path

import cv2

VIDEO_DIR = Path("data/videos")
OUTPUT_DIR = Path("analysis_frames")
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".webm", ".m4v"}


def find_videos(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    videos = [
        p
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
    ]
    return sorted(videos)


def inspect_video(video_path: Path, output_dir: Path) -> bool:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"  ERROR: could not open {video_path.name}")
        return False

    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_sec = (total_frames / fps) if fps > 0 else 0.0

    print(f"  filename:      {video_path.name}")
    print(f"  duration:      {duration_sec:.2f} s")
    print(f"  fps:           {fps:.2f}")
    print(f"  resolution:    {width}x{height}")
    print(f"  total frames:  {total_frames}")

    if total_frames <= 0:
        print("  ERROR: no frames in video")
        cap.release()
        return False

    middle_idx = total_frames // 2
    cap.set(cv2.CAP_PROP_POS_FRAMES, middle_idx)
    ok, frame = cap.read()
    cap.release()

    if not ok or frame is None:
        print(f"  ERROR: could not read frame at index {middle_idx}")
        return False

    output_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"{video_path.stem}_middle.jpg"
    out_path = output_dir / out_name
    if not cv2.imwrite(str(out_path), frame):
        print(f"  ERROR: failed to write {out_path}")
        return False

    print(f"  saved frame:   {out_path} (frame {middle_idx})")
    return True


def main() -> None:
    videos = find_videos(VIDEO_DIR)
    if not videos:
        print(f"No videos found under {VIDEO_DIR.resolve()}")
        return

    print(f"Found {len(videos)} video(s) in {VIDEO_DIR.resolve()}\n")

    ok_count = 0
    for i, path in enumerate(videos, start=1):
        try:
            rel = path.relative_to(VIDEO_DIR)
        except ValueError:
            rel = path.name
        print(f"[{i}/{len(videos)}] {rel}")
        if inspect_video(path, OUTPUT_DIR):
            ok_count += 1
        print()

    print(f"Done: {ok_count}/{len(videos)} processed. Frames in {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
