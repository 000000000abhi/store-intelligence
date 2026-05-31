import httpx
import json
import asyncio

async def ingest(file_path, url):
    with open(file_path, 'r') as f:
        events = [json.loads(line) for line in f if line.strip()]
        
    async with httpx.AsyncClient() as client:
        # Batch by 500
        for i in range(0, len(events), 500):
            batch = events[i:i+500]
            resp = await client.post(url, json={"events": batch})
            print(f"Batch {i//500}: {resp.status_code}")

if __name__ == "__main__":
    asyncio.run(ingest("/data/events/STORE_BLR_002.jsonl", "http://localhost:8000/events/ingest"))
