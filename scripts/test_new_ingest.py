import json
import httpx

import os

script_dir = os.path.dirname(__file__)
file_path = os.path.join(script_dir, '..', 'Resources', 'sample_eventsbe42122.jsonl')
with open(file_path) as f:
    events = [json.loads(line) for line in f if line.strip()]

r = httpx.post("http://localhost:8000/events/ingest", json=events)
print(f"Status: {r.status_code}")
print(r.json())
