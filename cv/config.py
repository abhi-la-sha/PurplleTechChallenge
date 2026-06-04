
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


YOLO_MODEL: str = "yolov8n.pt"
YOLO_CONFIDENCE: float = 0.35
PERSON_CLASS_ID: int = 0


SKIP_FRAMES: int = 3


EVENT_API_URL: str = "http://localhost:8000"
INGEST_ENDPOINT: str = "/events/ingest"
BATCH_SIZE: int = 50
MAX_RETRIES: int = 3
RETRY_DELAY_S: float = 2.0
REQUEST_TIMEOUT_S: float = 15.0


DATA_DIR: Path = Path("data/videos")
OUTPUT_DIR: Path = Path("analysis_frames")


ZONE_DWELL_EMIT_INTERVAL_S: int = 30
ZONE_LOST_TRACK_TIMEOUT_S: float = 2.0
REENTRY_WINDOW_S: float = 60.0
REENTRY_POSITION_THRESHOLD: float = 0.25


STORE_MAPPINGS: dict[str, str] = {
    "store1": "STORE_001",
    "store2": "STORE_002",
}



@dataclass
class StaffColorConfig:
    
    color_name: str
    method: Literal["dark", "hue"]
    # dark method params
    dark_v_thresh: int = 70       
    dark_fraction: float = 0.40   
    # hue method params
    hue_min: int = 0             
    hue_max: int = 0
    sat_min: int = 100           
    val_min: int = 80             
    hue_fraction: float = 0.30    


STAFF_COLOR_CONFIG: dict[str, StaffColorConfig] = {
    
    "STORE_001": StaffColorConfig(
        color_name="black",
        method="dark",
        dark_v_thresh=70,
        dark_fraction=0.40,
    ),

    "STORE_002": StaffColorConfig(
        color_name="pink",
        method="hue",
        hue_min=145,
        hue_max=175,
        sat_min=100,
        val_min=80,
        hue_fraction=0.30,
    ),
}

@dataclass
class VideoConfig:

    filename: str
    video_type: Literal["entry", "zone", "billing"]
    zone_id: str | None
    camera_id: str
    invert_crossing: bool = False
    line_y: float = 0.50
    clip_start: str | None = None



VIDEO_MAPPINGS: dict[str, list[VideoConfig]] = {
    "STORE_001": [
        VideoConfig(
            filename="entry.mp4",
            video_type="entry",
            zone_id=None,
            camera_id="STORE_001_CAM_ENTRY",
            invert_crossing=True,   
            line_y=0.52,
            clip_start="2026-04-10T20:00:00Z",
        ),
        VideoConfig(
            filename="zone 1.mp4",
            video_type="zone",
            zone_id="ZONE_1",
            camera_id="STORE_001_CAM_ZONE_1",
            clip_start="2026-04-10T20:00:00Z",
        ),
        VideoConfig(
            filename="zone 2.mp4",
            video_type="zone",
            zone_id="ZONE_2",
            camera_id="STORE_001_CAM_ZONE_2",
            clip_start="2026-04-10T20:00:00Z",
        ),
        VideoConfig(
            filename="billing_area.mp4",
            video_type="billing",
            zone_id="BILLING",
            camera_id="STORE_001_CAM_BILLING",
            clip_start="2026-04-10T20:00:00Z",
        ),
    ],
    "STORE_002": [
        VideoConfig(
            filename="entry 1.mp4",
            video_type="entry",
            zone_id=None,
            camera_id="STORE_002_CAM_ENTRY_1",
            invert_crossing=False,  
            line_y=0.45,
            clip_start="2026-03-29T19:30:00Z",
        ),
        VideoConfig(
            filename="entry 2.mp4",
            video_type="entry",
            zone_id=None,
            camera_id="STORE_002_CAM_ENTRY_2",
            invert_crossing=False,
            line_y=0.45,
            clip_start="2026-03-08T13:30:00Z",
        ),
        VideoConfig(
            filename="zone.mp4",
            video_type="zone",
            zone_id="ZONE",
            camera_id="STORE_002_CAM_ZONE",
            clip_start="2026-03-08T15:20:00Z",
        ),
        VideoConfig(
            filename="billing_area.mp4",
            video_type="billing",
            zone_id="BILLING",
            camera_id="STORE_002_CAM_BILLING",
            clip_start="2026-03-08T18:20:00Z",
        ),
    ],
}


COLOUR_CUSTOMER = (0, 200, 0)      # green
COLOUR_STAFF = (0, 140, 255)       # orange
COLOUR_ENTRY_LINE = (0, 0, 255)    # red
COLOUR_BILLING_REGION = (255, 0, 0)  # blue
COLOUR_TEXT_BG = (20, 20, 20)
COLOUR_TEXT_FG = (255, 255, 255)