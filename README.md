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
*Note: The detection pipeline is intentionally decoupled from `docker compose up` to match the PDF requirements ("docker compose up starts the API") and to prevent heavy AI models (YOLOv8) from locking up reviewer machines lacking GPU configuration.*

Once the API is healthy, you can trigger the computer vision pipeline to start processing CCTV footage. By default, it runs in **Auto-Discovery Mode**, finding and processing every `.mp4` file for all stores sequentially:
```bash
docker compose run pipeline python run_pipeline.py
```

If you only want to process a specific camera, you can pass arguments:
```bash
# Process Store 1 - Camera 3 (Entry) only
docker compose run pipeline python run_pipeline.py \
    --video "/data/Store 1-20260602T101818Z-3-001ec38db8/Store 1/CAM 3 - entry.mp4" \
    --camera-id CAM_3 \
    --store-id ST1001
```
*(Ensure the data is present in the `Resources/` directory mapped at the project root.)*

### 4. View Dashboard
Navigate to `http://localhost:3000` to see real-time updates as the pipeline pushes `ZONE_ENTER` and `BILLING_QUEUE_JOIN` events! The API dynamically normalizes incoming payloads, handling both strict PDF schemas and unstructured real-world JSON logs on the fly.
