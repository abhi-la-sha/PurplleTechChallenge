# CV Pipeline — Purplle Store Intelligence

Processes CCTV footage for two stores and emits behavioural events into the analytics API.

## Setup

```bash
pip install ultralytics supervision opencv-python requests
```

## Run all stores

```bash
# Dry run (prints events, no API calls)
python -m cv.batch_runner --dry-run

# Full run against local API
python -m cv.batch_runner

# GPU acceleration
python -m cv.batch_runner --device cuda

# One store only
python -m cv.batch_runner --store STORE_001
```

Run from the project root (same level as `data/` and `cv/`).

## Expected data layout

```
data/videos/
  store1/
    entry.mp4
    zone 1.mp4
    zone 2.mp4
    billing_area.mp4
  store2/
    entry 1.mp4
    entry 2.mp4
    zone.mp4
    billing_area.mp4
```

## Output

Annotated videos written to:

```
analysis_frames/
  store1/
    entry_annotated.mp4
    zone 1_annotated.mp4
    zone 2_annotated.mp4
    billing_area_annotated.mp4
  store2/
    entry 1_annotated.mp4
    entry 2_annotated.mp4
    zone_annotated.mp4
    billing_area_annotated.mp4
```

## Configuration

All config lives in `cv/config.py`:

| Key | Default | Description |
|-----|---------|-------------|
| `YOLO_MODEL` | `yolov8n.pt` | Model weights |
| `YOLO_CONFIDENCE` | `0.35` | Detection threshold |
| `SKIP_FRAMES` | `3` | Process every Nth frame |
| `EVENT_API_URL` | `http://localhost:8000` | API base URL |
| `ZONE_DWELL_EMIT_INTERVAL_S` | `30` | Seconds between ZONE_DWELL events |

Store-specific `line_y` (entry threshold) calibrated from analysis_frames:
- STORE_001 entry: `0.52` (inside=top, outside=bottom)
- STORE_002 entry 1/2: `0.45` (outside=top, inside=bottom)

Adjust in `VIDEO_MAPPINGS` inside `config.py` if your footage differs.

## Staff detection

| Store | Uniform | Method |
|-------|---------|--------|
| STORE_001 | Black | Dark pixel fraction (HSV Value < 70) |
| STORE_002 | Pink/Magenta | Hue range 145–175 in OpenCV HSV |

## API endpoint used

`POST /events/ingest` — idempotent batch ingest (up to 500 events per call).
Events are deduplicated server-side by `event_id`.