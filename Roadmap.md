# Project Roadmap

## Phase 0

Dataset Analysis

Completed:

* Camera mapping
* Store layout analysis
* Event identification

---

## Phase 1

Backend Foundation

Goals:

* FastAPI setup
* PostgreSQL setup
* SQLAlchemy setup
* Alembic setup
* Docker support
* Health endpoint
* Structured logging
* Testing foundation

Deliverables:

* Runnable backend
* Docker Compose
* Passing tests

---

## Phase 2

Event Schema & Database Models

Goals:

* Define event schema
* Create event models
* Create visitor session models
* Create transaction models

Deliverables:

* Event entities
* Database migrations

---

## Phase 3

Event Ingestion API

Goals:

* Event ingestion endpoint
* Validation
* Event persistence

Deliverables:

* POST /events

---

## Phase 4

Entry / Exit Detection

Camera:

* CAM3

Goals:

* Person detection
* Tracking
* Line crossing logic

Events:

* ENTRY
* EXIT

---

## Phase 5

Metrics Engine

Goals:

* Unique visitors
* Footfall
* Session analytics

Endpoints:

* /metrics

---

## Phase 6

Zone Analytics

Cameras:

* CAM1
* CAM2

Events:

* ZONE_ENTER
* ZONE_EXIT
* ZONE_DWELL

Endpoints:

* /heatmap

---

## Phase 7

Billing Analytics

Camera:

* CAM5

Events:

* BILLING_QUEUE_JOIN
* BILLING_QUEUE_ABANDON

Goals:

* Queue depth
* Queue analytics

---

## Phase 8

POS Correlation

Goals:

* Conversion rate
* Purchase correlation

Deliverables:

* Conversion metrics
* Funnel analytics

---

## Phase 9

Anomaly Detection

Goals:

* Queue spike detection
* Conversion drop detection
* Dead zone detection

Endpoints:

* /anomalies

---

## Phase 10

Dashboard

Goals:

* Live metrics
* Funnel visualization
* Heatmaps
* Anomalies

Technology:

* Streamlit

---

## Phase 11

Re-ID and Advanced Features

Goals:

* Reentry detection
* Cross-camera correlation

Status:

* Optional if time permits

---

## Phase 12

Testing & Documentation

Goals:

* Unit tests
* Integration tests
* DESIGN.md
* CHOICES.md
* Final submission
