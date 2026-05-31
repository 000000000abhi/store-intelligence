# System Architecture Documentation

**Project:** Purplle Tech Challenge 2026
**Store Focus:** Brigade Road, Bangalore (ST1008 / STORE_BLR_002)

---

## 1. High-Level System Overview
The Store Intelligence framework converts high-throughput raw CCTV streams into structured, queryable retail analytics. The platform is designed around a decoupled, event-driven microservices architecture that prioritizes resilience, asynchronous state reconstruction, and low latency.

```mermaid
graph TD
    %% Define Styles
    classDef container fill:#2d3436,stroke:#74b9ff,stroke-width:2px,color:#fff;
    classDef database fill:#0984e3,stroke:#fff,stroke-width:2px,color:#fff;
    classDef api fill:#6c5ce7,stroke:#fff,stroke-width:2px,color:#fff;
    classDef cache fill:#d63031,stroke:#fff,stroke-width:2px,color:#fff;

    %% Nodes
    subgraph "Edge / Store Location"
        A[CCTV Video Streams]:::container
    end
    
    subgraph "Computer Vision Pipeline (Docker)"
        B[Object Detection <br/> YOLOv8s]:::container
        C[Tracker <br/> ByteTrack]:::container
        D[Feature Extractor <br/> HSV Histogram]:::container
        E[Spatial Logic <br/> Shapely Polygons]:::container
    end

    subgraph "Core Backend Services (Docker)"
        F{Intelligence API <br/> FastAPI}:::api
        G[(PostgreSQL 15)]:::database
        H[(Redis 7)]:::cache
        I[POS Worker Thread]:::container
        K[Static Data: pos_transactions.csv]:::container
    end

    subgraph "Client"
        J[Vanilla JS Dashboard]:::container
    end

    %% Relationships
    A -->|RTSP / MP4| B
    B -->|BBoxes| C
    C -->|Crops| D
    D -->|Centroids| E
    E -->|POST /events/ingest <br/> JSONL Batch| F
    
    F -->|Ingest & Reconstruct State| G
    F -.->|Broadcast Live Counts| H
    K -.-> I
    I -->|Async Correlation| G
    H -->|WebSockets| J
    J -->|REST GET /metrics| F
```

---

## 2. Component Deep Dive

### 2.1 Computer Vision Pipeline (`pipeline/`)
The CV pipeline operates strictly within CPU environments to satisfy extreme scale constraints, operating completely free of GPU dependencies.

```mermaid
sequenceDiagram
    participant Camera
    participant YOLOv8
    participant ByteTrack
    participant ReID
    participant ZoneLogic
    participant FastAPI

    Camera->>YOLOv8: Frame (Every 5th)
    YOLOv8->>ByteTrack: Bounding Boxes & Confidence
    ByteTrack->>ReID: Track ID & Image Crop
    ReID-->>ByteTrack: Cosine Similarity Match (If Re-Entry)
    ByteTrack->>ZoneLogic: Track ID & Centroid (x, y)
    ZoneLogic->>FastAPI: POST /events/ingest (Event Batch)
```

* **Detector (YOLOv8s):** Chosen for its balance of CPU inference speed and accuracy. By sampling only every 5th frame, we maintain high throughput while conserving CPU cycles.
* **Tracker (Supervision ByteTrack):** Solves the immediate occlusion problem. ByteTrack leverages Kalman filters to predict an object's trajectory when obscured by store shelves, retaining the unique tracking ID upon re-emergence.
* **Person Re-ID (HSV Histogram Fallback):** Rather than utilizing large deep-learning models (`torchreid`), which heavily bloat Docker images, the pipeline calculates a 96-dimensional Color Histogram from the HSV color space.
* **Spatial Logic (Shapely):** Parses `store_layout.json` to construct strict `Polygon` objects. Tracking centroids are tested against these spatial boundaries to emit precision `ZONE_ENTER` events.

### 2.2 The Intelligence Backend (`app/`)
The FastAPI application acts as the nerve center.

```mermaid
sequenceDiagram
    participant CV Pipeline
    participant FastAPI
    participant PostgreSQL
    participant Redis
    participant Dashboard

    CV Pipeline->>FastAPI: POST /events/ingest
    FastAPI->>PostgreSQL: INSERT into Events (Idempotent)
    FastAPI->>PostgreSQL: UPSERT VisitorSession State
    PostgreSQL-->>FastAPI: Commit OK
    FastAPI->>Redis: PUBLISH live_metrics {"visitors": 3}
    Redis->>Dashboard: WebSocket Broadcast
```

* **Ingest-Time Session Reconstruction:** Flat events are intercepted at `POST /events/ingest` and funneled through a strict state machine, live-updating the `visitor_sessions` PostgreSQL table.
* **Idempotency:** PostgreSQL uses `ON CONFLICT DO NOTHING` on the primary `event_id`. Re-pushed batches are safely ignored, preventing data corruption.

---

## 3. Data Flow & Metrics State Machine

Our North Star metric—Conversion Rate—depends on precise chronological session flows. 

```mermaid
stateDiagram-v2
    [*] --> ENTERED: ENTRY Event
    ENTERED --> ZONE_VISIT: ZONE_ENTER Event
    ZONE_VISIT --> BILLING_QUEUE: BILLING_QUEUE_JOIN
    
    BILLING_QUEUE --> PURCHASED: POS Match Found
    BILLING_QUEUE --> ABANDONED: 5 Min Timeout (Worker)
    
    ENTERED --> EXITED: EXIT Event
    ZONE_VISIT --> EXITED: EXIT Event
    PURCHASED --> EXITED: EXIT Event
    ABANDONED --> EXITED: EXIT Event
    
    EXITED --> ENTERED: REENTRY Event (Within 15m)
    EXITED --> [*]
```

By explicitly mapping user flows into states, our API endpoints like `GET /stores/{id}/metrics` achieve consistent sub-15ms response times. Instead of grouping thousands of raw events at runtime, we perform simple aggregations on pre-computed session states.
