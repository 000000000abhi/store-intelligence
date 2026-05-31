#!/usr/bin/env python3
"""
ingest_sample_data.py — Ingests sample_events.jsonl into the Store Intelligence API.

Usage:
    python scripts/ingest_sample_data.py [--api-url http://localhost:8000] [--batch-size 50]

This script reads Resources/sample_events.jsonl and POSTs events in batches
to /events/ingest, providing immediate dashboard data without needing the CV pipeline.
"""

import json
import sys
import time
import argparse
import os
import requests

# Resolve paths relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_JSONL = os.path.join(REPO_ROOT, "Resources", "sample_events.jsonl")


def ingest(api_url: str, jsonl_path: str, batch_size: int):
    print(f"\n{'='*60}")
    print(f"  Store Intelligence — Sample Data Ingestion")
    print(f"{'='*60}")
    print(f"  API:    {api_url}")
    print(f"  File:   {jsonl_path}")
    print(f"  Batch:  {batch_size} events/request\n")

    if not os.path.exists(jsonl_path):
        print(f"  ✗ File not found: {jsonl_path}")
        sys.exit(1)

    # Load all events
    events = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))

    total = len(events)
    print(f"  Loaded {total} events from file.")

    accepted_total = 0
    rejected_total = 0
    batch_num = 0

    for i in range(0, total, batch_size):
        batch = events[i : i + batch_size]
        batch_num += 1
        try:
            resp = requests.post(
                f"{api_url}/events/ingest",
                json=batch,
                timeout=10,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                body = resp.json()
                accepted = body.get("accepted", 0)
                rejected = body.get("rejected", 0)
                errors = body.get("errors", [])
                accepted_total += accepted
                rejected_total += rejected
                status = "[OK]" if rejected == 0 else "[WARN]"
                print(f"  {status} Batch {batch_num:3d}: accepted={accepted}, rejected={rejected}", end="")
                if errors:
                    print(f"  errors={errors[:2]}", end="")
                print()
            else:
                print(f"  [FAIL] Batch {batch_num}: HTTP {resp.status_code} - {resp.text[:200]}")
                rejected_total += len(batch)
        except requests.exceptions.ConnectionError:
            print(f"  [FAIL] Cannot connect to {api_url}. Is the backend running?")
            sys.exit(1)
        except Exception as e:
            print(f"  [FAIL] Batch {batch_num} error: {e}")
            rejected_total += len(batch)

        # Small delay to avoid overwhelming the API
        time.sleep(0.1)

    print(f"\n{'='*60}")
    print(f"  Done: {accepted_total} accepted, {rejected_total} rejected out of {total} total")
    print(f"{'='*60}\n")

    if accepted_total > 0:
        print("  [OK] Data ingested successfully! Refresh the dashboard to see metrics.\n")
    else:
        print("  [FAIL] No events were accepted. Check backend logs for errors.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest sample_events.jsonl into the Store Intelligence API")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Backend API base URL")
    parser.add_argument("--batch-size", type=int, default=50, help="Events per request batch")
    parser.add_argument("--file", default=DEFAULT_JSONL, help="Path to .jsonl file")
    args = parser.parse_args()

    ingest(args.api_url, args.file, args.batch_size)
