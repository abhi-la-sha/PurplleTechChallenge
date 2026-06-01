# Store Intelligence Platform

## Overview

This project is being built for a retail analytics challenge.

The goal is to transform CCTV footage into actionable store intelligence by generating visitor events, computing retail metrics, and exposing analytics through APIs and dashboards.

## Business Objective

Calculate and analyze:

* Store footfall
* Visitor sessions
* Zone engagement
* Dwell time
* Queue analytics
* Conversion rate
* Funnel analytics
* Anomaly detection

## Available Data

### CCTV Cameras

#### CAM1

Purpose: Product Analytics

Visible Areas:

* Product shelves
* Customer browsing zones

Expected Events:

* ZONE_ENTER
* ZONE_EXIT
* ZONE_DWELL

---

#### CAM2

Purpose: Product Analytics

Visible Areas:

* Product shelves
* Customer browsing zones

Expected Events:

* ZONE_ENTER
* ZONE_EXIT
* ZONE_DWELL

---

#### CAM3

Purpose: Entry / Exit Monitoring

Expected Events:

* ENTRY
* EXIT
* REENTRY (future)

---

#### CAM4

Purpose: Auxiliary Camera

Used for:

* Future enhancements
* Not part of MVP

---

#### CAM5

Purpose: Billing Analytics

Expected Events:

* BILLING_QUEUE_JOIN
* BILLING_QUEUE_ABANDON

### Store Layout

Store layout is provided.

The layout contains:

* Product sections
* Makeup unit
* Cash counter
* Entry area

The layout will be used to define retail zones.

### POS Data

Transaction CSV is available.

Future logic will correlate:

* Billing activity
* Transaction timestamps

to compute conversion rate.

---

## Event Driven Architecture

All analytics must be derived from generated events.

Example events:

* ENTRY
* EXIT
* ZONE_ENTER
* ZONE_EXIT
* ZONE_DWELL
* BILLING_QUEUE_JOIN
* BILLING_QUEUE_ABANDON
* REENTRY

No hardcoded metrics should exist.

---

## Technology Stack

Backend:

* FastAPI
* PostgreSQL
* SQLAlchemy
* Alembic
* Pydantic

Computer Vision:

* YOLOv8
* ByteTrack

Dashboard:

* Streamlit

Containerization:

* Docker
* Docker Compose

Testing:

* Pytest

---

## Architecture Principles

Use Clean Architecture.

Flow:

Route
→ Service
→ Repository
→ Database

Requirements:

* Async first
* Dependency injection
* Structured logging
* Typed code
* Modular design

Business logic must not exist in API routes.

Future phases will extend the foundation without major refactoring.
