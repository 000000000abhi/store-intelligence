import json
import httpx

with open(r'c:\Users\abhijeet.ansal\Desktop\purpelle\store-intelligence\Resources\sample_eventsbe42122.jsonl') as f:
    events = [json.loads(line) for line in f if line.strip()]

r = httpx.post("http://localhost:8000/events/ingest", json=events)
print(f"Status: {r.status_code}")
print(r.json())
