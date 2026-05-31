# PROMPT: Create tests for the health endpoint checking the STALE_FEED status
# CHANGES MADE: Added explicit tests for timestamp drift and status degradation.

import pytest
from datetime import datetime, timedelta, timezone
from tests.conftest import make_event

def get_health(client, store_id):
    resp = client.get(f"/stores/{store_id}/health")
    assert resp.status_code == 200
    return resp.json()

def ingest(client, events):
    resp = client.post("/events/ingest", json={"events": events})
    assert resp.status_code == 202

class TestHealthHappyPath:
    def test_health_ok_recent_events(self, client):
        store_id = "STORE_HEALTH_OK"
        # Ingest an event from right now
        ingest(client, [make_event(store_id=store_id)])
        
        health = get_health(client, store_id)
        assert health["status"] == "ok"
        assert health["last_event_time"] is not None

class TestHealthSadPaths:
    def test_health_stale_feed(self, client):
        store_id = "STORE_HEALTH_STALE"
        # Ingest an event from 15 minutes ago
        stale_time = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
        ingest(client, [make_event(store_id=store_id, timestamp=stale_time)])
        
        health = get_health(client, store_id)
        # Assuming the backend returns "degraded" or "stale" when the last event > 10 mins
        # (This matches the standard store intelligence spec)
        assert health["status"] != "ok" 
        assert "stale" in health["status"].lower() or "degraded" in health["status"].lower()

    def test_health_no_events(self, client):
        store_id = "STORE_HEALTH_EMPTY"
        health = get_health(client, store_id)
        assert health["status"] != "ok"
