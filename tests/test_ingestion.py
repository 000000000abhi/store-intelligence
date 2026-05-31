# PROMPT: Create tests for event ingestion covering idempotency and partial success
# CHANGES MADE: Added explicit tests for ON CONFLICT DO NOTHING and batching logic.

import uuid
import pytest
from tests.conftest import make_event

def ingest(client, events):
    return client.post("/events/ingest", json={"events": events})

class TestIngestionHappyPath:
    def test_ingest_valid_batch(self, client):
        events = [make_event(visitor_id=f"VIS_{i}") for i in range(5)]
        resp = ingest(client, events)
        assert resp.status_code == 202
        data = resp.json()
        assert data["accepted"] == 5
        assert data["rejected"] == 0
        assert len(data["errors"]) == 0

class TestIngestionIdempotency:
    def test_duplicate_events_ignored(self, client):
        event_id = str(uuid.uuid4())
        events = [make_event(event_id=event_id)]
        
        # First ingest
        resp1 = ingest(client, events)
        assert resp1.status_code == 202
        assert resp1.json()["accepted"] == 1
        
        # Second ingest - exact same event_id
        resp2 = ingest(client, events)
        assert resp2.status_code == 202
        assert resp2.json()["accepted"] == 0
        assert resp2.json()["rejected"] == 1

class TestIngestionSadPaths:
    def test_empty_batch(self, client):
        resp = ingest(client, [])
        assert resp.status_code == 202
        assert resp.json()["accepted"] == 0
        assert "Empty batch" in resp.json()["errors"]

    def test_schema_validation_failure(self, client):
        # Missing required fields like store_id
        bad_event = {"event_id": str(uuid.uuid4())}
        resp = ingest(client, [bad_event])
        # FastAPI returns 422 Unprocessable Entity
        assert resp.status_code == 422
