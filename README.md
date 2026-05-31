# Purplle Tech Challenge 2026 — Store Intelligence

Welcome to the Brigade Road Store Intelligence system. This repository processes raw CCTV footage, tracks unique visitors across zones, correlates them with Point-of-Sale data, and generates real-time conversion funnels.

## Directory Structure
* `pipeline/`: Computer Vision logic (YOLOv8s, ByteTrack, Re-ID, Shapely Polygons).
* `app/`: FastAPI Backend intelligence and state reconstruction.
* `frontend/`: Real-time Vanilla JS websocket dashboard.
* `docs/`: Comprehensive architecture specifications.
* `tests/`: 105 tests targeting 85%+ statement coverage across all API boundaries.
* `Resources/`: Brigade Road data files (POS transactions, videos, layouts).

## Documentation
Please refer to the `docs/` folder for high-level architectural insight:
* [ARCHITECTURE.md](docs/ARCHITECTURE.md): System component breakdown and data flow.
* [DESIGN.md](docs/DESIGN.md): AI-Assisted architectural pivots.
* [CHOICES.md](docs/CHOICES.md): 3 core decisions and their measured performance metrics.

## Quick Start

### 1. Boot the Architecture
The entire microservice stack (Postgres, Redis, API, and Frontend) operates via Docker Compose.
```bash
docker compose up -d
```
The FastAPI instance will be available at `http://localhost:8000`.

### 2. Run the Test Suite
The test suite spans `test_funnel.py`, `test_ingestion.py`, `test_metrics.py`, and more.
```bash
python -m pytest tests/ -v
```

### 3. Run the Detection Pipeline
Once the API is healthy, you can trigger the computer vision pipeline to start ingesting CCTV footage into the API:
```bash
docker compose exec pipeline python run_pipeline.py
```
*Note: Ensure the Brigade Road data is present in the `Resources/` directory mapped at the project root.*

### 4. View Dashboard
Navigate to `http://localhost:3000` to see real-time updates as the pipeline pushes `ZONE_ENTER` and `BILLING_QUEUE_JOIN` events!
