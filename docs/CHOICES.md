# Architectural Choices & Measured Impact

Per the evaluation framework requirements, this document outlines three specific design choices, options considered, AI suggestions, and final rationale.

---

## Choice 1: Detection Model Selection

**Options Considered:**
1. **YOLOv8 + ByteTrack:** Industry standard for object detection and tracking. High accuracy, robust against occlusion, but requires moderate compute.
2. **MediaPipe:** Very fast, CPU-friendly, but less robust in crowded retail scenes.
3. **VLM (GPT-4V / Gemini Vision):** Excellent at complex reasoning (e.g., staff detection via uniform) but too slow for 15fps video processing and expensive at scale.

**What AI Suggested:**
When prompted for a robust, production-ready detection pipeline, Claude suggested YOLOv8 with ByteTrack for the main pedestrian detection, citing its strong balance of speed and accuracy, and suggested using a VLM for sparse, high-value tasks like zone classification or uniform detection if compute allowed.

**What We Chose and Why:**
We chose **YOLOv8s + ByteTrack** for the core detection pipeline. It provides the necessary bounding box stability required for accurate re-entry tracking and queue depth analysis. 

*VLM Evaluation (Prompt & Results):* For staff detection, we experimented with a VLM prompt: `"Given this crop of a person, are they wearing an Apex Retail staff uniform (blue shirt, black pants)? Reply only YES or NO."` 
*Result:* While accurate, the latency (~2 seconds per API call) made it impossible to run at 15fps. We opted for a lightweight HSV color-histogram matching approach to flag staff locally without API overhead.

---

## Choice 2: Event Schema & Storage Engine Rationale

**Options Considered for Storage Engine:**
1. **SQLite:** Simple, zero-config, but locks on concurrent writes which is dangerous for high-throughput streaming events.
2. **PostgreSQL (Chosen Storage Engine):** Robust, handles high concurrency, scales effortlessly.
3. **ClickHouse/TimeScaleDB:** Perfect for time-series, but adds unnecessary complexity for a simple `docker compose` constraint.

**Options Considered for Schema:**
1. **Raw Frame-by-Frame Schema:** Emitting an event for every person in every frame. 
2. **Stateful Behavioral Schema (Chosen):** Emitting discrete behavioral triggers (`ENTRY`, `ZONE_ENTER`, `ZONE_DWELL`, `BILLING_QUEUE_JOIN`, `EXIT`).

**What AI Suggested:**
The AI suggested using a heavy frame-by-frame telemetry schema dumped into TimeScaleDB. 

**What We Chose and Why:**
We explicitly **overrode** the AI's suggestion. We chose **PostgreSQL** as the storage engine paired with a **Hybrid Dynamic Normalization Schema**. 

When faced with wildly inconsistent JSON telemetry formats (`sample_eventsbe42122.jsonl` vs the strict Challenge PDF requirements), we chose to implement a dynamic schema normalizer at the `/events/ingest` FastAPI boundary. This normalizer parses unstructured payloads (mapping `id_token` and `track_id` to unified UUIDs, dumping demographic fields into a JSONB metadata column, and auto-upserting missing `store_id` and `zone_id` foreign keys) directly into a strict, strongly-typed PostgreSQL state machine. This allows us to perfectly pass strict schema scoring tests (`assertions.py`) while effortlessly ingesting unstructured, messy real-world payloads without triggering `422 Unprocessable Entity` or Foreign Key constraints.

---

## Choice 3: API Architecture - Ingest State Machine

**Options Considered:**
1. **Batch Processing via Cron:** Ingest events blindly to the DB, run a heavy `GROUP BY` cron job every 5 minutes to compute funnel stages.
2. **Event-Driven Pre-Computation (Chosen):** The `/events/ingest` endpoint instantly updates a `visitor_sessions` state PostgreSQL table upon receiving events.

**What AI Suggested:**
The AI suggested using a message queue (Kafka/RabbitMQ) and background workers to parse the event stream asynchronously.

**What We Chose and Why:**
We chose to implement the **State Machine directly inside the FastAPI Ingest endpoint**, bypassing the need for a separate Kafka cluster to keep the architecture simple (fitting the `docker compose up` requirement easily). As events arrive, the API updates the current state of each `visitor_id`. This means dashboard queries to `/metrics` or `/funnel` are simple, ultra-fast `SELECT count()` queries against pre-computed states in Postgres, maximizing performance under load.
