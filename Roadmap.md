# Purplle Store Intelligence Platform Roadmap

## Project Overview

Build a multi-store retail intelligence platform that:

- Processes CCTV footage from multiple stores
- Detects customer movement and store interactions
- Generates retail analytics events
- Computes business metrics
- Detects operational anomalies
- Provides dashboards and visualizations

---

# Dataset

## Store 1

Videos:

- entry.mp4
- zone1.mp4
- zone2.mp4
- billing_area.mp4

Staff Uniform:

- Black uniform

---

## Store 2

Videos:

- entry1.mp4
- entry2.mp4
- zone.mp4
- billing_area.mp4

Staff Uniform:

- Pink shirt

---

## Output Videos

Annotated videos will be generated in:

analysis_frames/

- store1/
- store2/

Each processed video must generate an annotated version showing:

- Person detections
- Track IDs
- Staff/customer labels
- Events
- Statistics overlays

## Phase 0

Dataset Analysis

Completed:

- Camera mapping
- Store layout analysis
- Event identification

---

## Phase 1

Backend Foundation

Goals:

- FastAPI setup
- PostgreSQL setup
- SQLAlchemy setup
- Alembic setup
- Docker support
- Health endpoint
- Structured logging
- Testing foundation

Deliverables:

- Runnable backend
- Docker Compose
- Passing tests

---

## Phase 2

Event Schema & Database Models

Goals:

- Define event schema
- Create event models
- Create visitor session models
- Create transaction models

Deliverables:

- Event entities
- Database migrations

---

## Phase 3

Event Ingestion API

Goals:

- Event ingestion endpoint
- Validation
- Event persistence

Deliverables:

- POST /events

---

## Phase 4

## Goals

### Store-Aware Metrics

Add:

GET /stores/{store_id}/metrics

Requirements:

- Filter analytics by store
- Support multiple stores
- Preserve existing metrics functionality

### Idempotent Event Ingestion

Add:

POST /events/ingest

Requirements:

- Accept up to 500 events
- Detect duplicate event_id values
- Skip duplicates silently
- Return ingestion summary

Example:

{  
"ingested": 490,  
"duplicates": 10,  
"errors": []  
}

### Infrastructure Validation

Verify:

- Docker Compose startup
- Database migrations
- API startup
- End-to-end workflow

Deliverables:

- Store-aware metrics
- Idempotent ingestion
- Verified deployment

---

# Phase 5:

## Funnel Analytics

Endpoint:

GET /stores/{store_id}/funnel

Stages:

ENTRY

↓

ZONE_ENTER

↓

BILLING_QUEUE_JOIN

↓

PURCHASE

Metrics:

- Total sessions
- Funnel counts
- Conversion rates
- Drop-off percentages

Deliverables:

- Funnel endpoint
- Funnel aggregation service

---

## Heatmap Analytics

Endpoint:

GET /stores/{store_id}/heatmap

Per Zone:

- Visit count
- Average dwell time
- Normalized popularity score

Requirements:

- Normalize scores between 0–100
- Set data_confidence=false if fewer than 20 sessions

Deliverables:

- Heatmap endpoint
- Zone analytics service

---

# Phase 6: Anomaly detection

Endpoint:

GET /stores/{store_id}/anomalies

Supported Anomalies:

### BILLING_QUEUE_SPIKE

Condition:

- Queue depth exceeds threshold

Severity:

- WARN
- CRITICAL

---

### CONVERSION_DROP

Condition:

- Current conversion below rolling average

Severity:

- WARN
- CRITICAL

---

### DEAD_ZONE

Condition:

- No zone activity within configured window

Severity:

- INFO
- WARN

Response:

{  
"type": "DEAD_ZONE",  
"severity": "WARN",  
"suggested_action": "...",  
"detected_at": "..."  
}

Deliverables:

- Anomaly engine
- Anomaly endpoint

---

# Phase 7: Health Monitoring

Endpoint:

GET /health

Enhancements:

Per Store:

- Last event timestamp
- Event freshness
- Feed status

Statuses:

- HEALTHY
- STALE_FEED

Rules:

- STALE_FEED if no events received in >10 minutes

Deliverables:

- Enhanced health endpoint

---

# Phase 8: Computer Vision Pipeline

## Architecture

cv/

- [detect.py](http://detect.py)
- [tracker.py](http://tracker.py)
- [emit.py](http://emit.py)
- batch_[runner.py](http://runner.py)
- [staff.py](http://staff.py)
- [config.py](http://config.py)
- [utils.py](http://utils.py)

---

## Person Detection

Technology:

- YOLOv8n
- ByteTrack (Supervision)

Features:

- Person detection
- Multi-person tracking
- Stable track IDs

---

## Entry / Exit Detection

Videos:

Store 1

- entry.mp4

Store 2

- entry1.mp4
- entry2.mp4

Generated Events:

- ENTRY
- EXIT

Method:

- Line-crossing detection

---

## Zone Analytics Detection

Videos:

Store 1

- zone1.mp4
- zone2.mp4

Store 2

- zone.mp4

Generated Events:

- ZONE_ENTER
- ZONE_EXIT
- ZONE_DWELL

Metrics:

- Zone popularity
- Dwell time

---

## Billing Analytics Detection

Videos:

Store 1

- billing_area.mp4

Store 2

- billing_area.mp4

Generated Events:

- BILLING_QUEUE_JOIN
- BILLING_QUEUE_ABANDON

Metrics:

- Queue depth
- Queue abandonment
- Queue trends

---

## Staff Detection

Store-specific uniform detection.

### Store 1

Uniform:

- Black

### Store 2

Uniform:

- Pink

Method:

1. Extract torso region
2. Convert to HSV
3. Compute dominant color
4. Compare against configured uniform color range

Output:

{  
"is_staff": true  
}

Staff events are stored but excluded from:

- Footfall
- Unique visitors
- Funnel analytics
- Conversion calculations

Reason:

Known uniform colors provide a simpler and more reliable solution than clustering.

---

## Event Emission

Endpoint:

POST /events/ingest

Requirements:

- Batched ingestion
- Retry logic
- Timeout handling
- Structured logging
- Idempotent event submission

---

## Annotated Video Generation

Required Deliverable

Output Location:

analysis_frames/

- store1/
- store2/

Generated Files:

- entry_annotated.mp4
- zone1_annotated.mp4
- zone2_annotated.mp4
- billing_area_annotated.mp4
- entry1_annotated.mp4
- entry2_annotated.mp4
- zone_annotated.mp4

Overlay Requirements:

- Bounding boxes
- Track IDs
- Detection confidence
- STAFF / CUSTOMER labels
- Event labels
- Entry/Exit lines
- Store identifier
- Processing statistics

Statistics Overlay:

- Active tracks
- Visitors
- Staff count
- Event count

Purpose:

- Visual validation
- Debugging
- Final demo presentation

Deliverables:

- Working CV pipeline
- Event generation
- Annotated videos

---

# Phase 9: Documentation

Required for evaluation.

## [DESIGN.md](http://DESIGN.md)

Include:

- System architecture
- Event flow
- Analytics architecture
- CV pipeline
- Data model

---

## [CHOICES.md](http://CHOICES.md)

Include:

- Technology decisions
- YOLOv8n selection
- ByteTrack selection
- FastAPI rationale
- PostgreSQL rationale
- Trade-offs
- Future improvements

Deliverables:

- [DESIGN.md](http://DESIGN.md)
- [CHOICES.md](http://CHOICES.md)

---

# Phase 10: Testing & Edge Cases

Add Tests For:

### Empty Store

Expected:

- Metrics return zero
- No failures

---

### All Staff Footage

Expected:

- Events stored
- Visitor metrics excluded

---

### Re-entry Handling

Expected:

- Same visitor not double-counted

---

### Idempotent Ingestion

Expected:

- Same batch submitted twice
- No duplicate records

---

### Multi-Store Isolation

Expected:

- Store metrics remain independent
- No cross-store contamination

Deliverables:

- Additional unit tests
- Additional integration tests

---

# Phase 11: Live Dashboard

Bonus Feature

Technology:

- Streamlit

or

- Rich terminal dashboard

Features:

- Live metrics
- Funnel visualization
- Heatmaps
- Queue analytics
- Anomaly alerts

Data Source:

Backend APIs

Deliverables:

- Live dashboard
- Bonus evaluation points

---

# Final Submission Checklist

## Backend

- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Docker

## APIs

- Metrics
- Funnel
- Heatmap
- Anomalies
- Health
- Event Ingestion

## Computer Vision

- YOLOv8n
- ByteTrack
- Staff Detection
- Event Generation

## Outputs

- Annotated Videos
- [DESIGN.md](http://DESIGN.md)
- [CHOICES.md](http://CHOICES.md)

## Quality

- Unit Tests
- Integration Tests
- Docker Validation

## Bonus

- Live Dashboard

---

## Success Criteria

The system should:

1. Process all provided store videos.
2. Generate retail analytics events.
3. Store events reliably.
4. Compute store-level business metrics.
5. Detect anomalies.
6. Produce annotated validation videos.
7. Demonstrate an end-to-end retail intelligence workflow.

