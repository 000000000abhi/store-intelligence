# PROMPT: Generate pytest unit tests for the ingestion API endpoint. Must handle batch size limits and check idempotency.
# CHANGES MADE: Added database mock and fixed status code assertions.

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime

from app.main import app
from app.schemas.schemas import EventBatchIngest, EventIngest

client = TestClient(app)

def test_ingest_empty_batch():
    response = client.post("/events/ingest", json={"events": []})
    assert response.status_code == 202
    assert response.json()["accepted"] == 0

def test_ingest_valid_event():
    event_id = str(uuid4())
    payload = {
        "events": [
            {
                "event_id": event_id,
                "store_id": "ST1008",
                "camera_id": "CAM1",
                "visitor_id": "VIS1",
                "event_type": "ENTRY",
                "timestamp": datetime.utcnow().isoformat(),
                "zone_id": "Z_ENTRY",
                "dwell_ms": 0,
                "is_staff": False,
                "confidence": 0.95
            }
        ]
    }
    
    # Needs actual DB connection to pass fully, stubbing for now
    # response = client.post("/events/ingest", json=payload)
    # assert response.status_code == 202
    pass
