#!/usr/bin/env python3
"""
export_event_log.py — Exports all real pipeline events from the PostgreSQL
database into a JSONL file matching the Purplle Tech Challenge schema.

Run this AFTER the pipeline has already processed the videos.
The database already has every detected event — this just exports them.

Usage (from repo root):
    python scripts/export_event_log.py

Or if the backend container is running:
    docker compose exec backend python /app/../scripts/export_event_log.py
"""

import json
import os
import sys
import psycopg2
from datetime import datetime, timedelta

# ── DB connection (matches docker-compose.yml environment) ────────────────────
DB_HOST = os.getenv("DB_HOST",     "localhost")
DB_PORT = os.getenv("DB_PORT",     "5432")
DB_NAME = os.getenv("DB_NAME",     "storedb")
DB_USER = os.getenv("DB_USER",     "storeuser")
DB_PASS = os.getenv("DB_PASS",     "storepassword")

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(REPO_ROOT, "event_log.jsonl")

# ── Zone metadata lookup ──────────────────────────────────────────────────────
ZONE_DEFAULTS = {
    "BILLING":       {"zone_name": "Billing Counter Queue", "zone_type": "BILLING"},
    "ZONE":          {"zone_name": "General Floor Zone",    "zone_type": "SHELF"},
}

def zone_meta(zone_id):
    if zone_id is None:
        return None, None, None
    if "BILLING" in zone_id.upper():
        return zone_id, "Billing Counter Queue", "BILLING"
    return zone_id, "General Floor Zone", "SHELF"

def infer_age_bucket(age):
    if age is None:
        return None
    if age < 25:
        return "18-24"
    if age < 35:
        return "25-34"
    if age < 45:
        return "35-44"
    return "45-54"

def main():
    print("Connecting to PostgreSQL at %s:%s/%s ..." % (DB_HOST, DB_PORT, DB_NAME))
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASS
        )
    except Exception as e:
        print("ERROR: Could not connect to database: %s" % e)
        print()
        print("Make sure the backend is running:")
        print("  docker compose up -d")
        print("Then run this script again.")
        sys.exit(1)

    cur = conn.cursor()

    # ── Fetch all events ordered by timestamp ─────────────────────────────────
    print("Fetching events from database...")
    cur.execute("""
        SELECT
            event_id,
            store_id,
            camera_id,
            visitor_id,
            event_type,
            timestamp,
            zone_id,
            dwell_ms,
            is_staff,
            confidence,
            metadata_json
        FROM events
        ORDER BY timestamp ASC
    """)
    rows = cur.fetchall()
    print("  Found %d events in database." % len(rows))

    if not rows:
        print("No events found. Make sure the pipeline has been run first.")
        conn.close()
        sys.exit(1)

    # ── Build visitor ID -> short id_token map ────────────────────────────────
    visitor_ids    = list(dict.fromkeys(r[3] for r in rows))  # ordered unique
    token_map      = {"ID_%d" % (60001 + i): vid for i, vid in enumerate(visitor_ids)}
    visitor_to_token = {vid: "ID_%d" % (60001 + i) for i, vid in enumerate(visitor_ids)}
    track_id_map   = {vid: (100 + i) for i, vid in enumerate(visitor_ids)}

    # ── Detect billing sessions (ENTRY -> BILLING_QUEUE_JOIN pairs) ───────────
    billing_joins = {}   # visitor_id -> {join row}
    output_events = []

    for row in rows:
        (event_id, store_id, camera_id, visitor_id, event_type,
         timestamp, zone_id, dwell_ms, is_staff, confidence, metadata) = row

        meta     = metadata or {}
        gender   = meta.get("gender_pred") or meta.get("gender")
        age      = meta.get("age_pred") or meta.get("age")
        age_bucket = meta.get("age_bucket") or infer_age_bucket(age)
        id_token = visitor_id if is_staff else visitor_to_token.get(visitor_id, visitor_id)
        track_id = track_id_map.get(visitor_id, 0)
        store_code = store_id.lower().replace("st", "store_") if store_id else "store_unknown"

        ev_upper = event_type.upper()

        # ── Map internal event types to challenge schema ───────────────────────
        if ev_upper in ("ENTRY", "REENTRY"):
            output_events.append({
                "event_type":      "entry",
                "id_token":        id_token,
                "store_code":      store_code,
                "camera_id":       camera_id,
                "event_timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                "is_staff":        is_staff,
                "gender_pred":     gender,
                "age_pred":        age,
                "age_bucket":      age_bucket,
                "is_face_hidden":  meta.get("is_face_hidden", False),
                "group_id":        meta.get("group_id"),
                "group_size":      meta.get("group_size"),
            })

        elif ev_upper == "EXIT":
            output_events.append({
                "event_type":      "exit",
                "id_token":        id_token,
                "store_code":      store_code,
                "camera_id":       camera_id,
                "event_timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                "is_staff":        is_staff,
                "gender_pred":     gender,
                "age_pred":        age,
                "age_bucket":      age_bucket,
                "is_face_hidden":  meta.get("is_face_hidden", False),
                "group_id":        meta.get("group_id"),
                "group_size":      meta.get("group_size"),
            })

        elif ev_upper in ("ZONE_ENTER", "ZONE_ENTERED"):
            zid, zname, ztype = zone_meta(zone_id)
            output_events.append({
                "event_type":      "zone_entered",
                "track_id":        track_id,
                "store_id":        store_id,
                "camera_id":       camera_id,
                "zone_id":         zid or "PURPLLE_MUM_1076_Z01",
                "zone_name":       zname or "General Floor Zone",
                "zone_type":       ztype or "SHELF",
                "is_revenue_zone": "Yes",
                "event_time":      timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                "zone_hotspot_x":  meta.get("hotspot_x", 300.0),
                "zone_hotspot_y":  meta.get("hotspot_y", 200.0),
                "gender":          gender,
                "age":             age,
                "age_bucket":      age_bucket,
            })

        elif ev_upper in ("ZONE_EXIT", "ZONE_EXITED"):
            zid, zname, ztype = zone_meta(zone_id)
            output_events.append({
                "event_type":      "zone_exited",
                "track_id":        track_id,
                "store_id":        store_id,
                "camera_id":       camera_id,
                "zone_id":         zid or "PURPLLE_MUM_1076_Z01",
                "zone_name":       zname or "General Floor Zone",
                "zone_type":       ztype or "SHELF",
                "is_revenue_zone": "Yes",
                "event_time":      timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                "zone_hotspot_x":  meta.get("hotspot_x", 300.0),
                "zone_hotspot_y":  meta.get("hotspot_y", 200.0),
                "gender":          gender,
                "age":             age,
                "age_bucket":      age_bucket,
            })

        elif ev_upper == "BILLING_QUEUE_JOIN":
            # Store join time — we will write the full event when we see the exit
            billing_joins[visitor_id] = {
                "join_ts":   timestamp,
                "track_id":  track_id,
                "store_id":  store_id,
                "camera_id": camera_id,
                "gender":    gender,
                "age":       age,
                "age_bucket": age_bucket,
                "dwell_ms":  dwell_ms,
                "meta":      meta,
            }

        elif ev_upper in ("PURCHASED", "BILLING_EXIT"):
            info = billing_joins.pop(visitor_id, None)
            if info:
                join_ts   = info["join_ts"]
                exit_ts   = timestamp
                wait_secs = max(0, int((exit_ts - join_ts).total_seconds()))
                output_events.append({
                    "queue_event_id":         str(event_id),
                    "event_type":             "queue_completed",
                    "track_id":               info["track_id"],
                    "store_id":               info["store_id"],
                    "camera_id":              info["camera_id"],
                    "zone_id":                "PURPLLE_MUM_1076_Z_BILLING_01",
                    "zone_name":              "Billing Counter Queue",
                    "zone_type":              "BILLING",
                    "is_revenue_zone":        "Yes",
                    "queue_join_ts":          join_ts.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                    "queue_served_ts":        timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                    "queue_exit_ts":          timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                    "wait_seconds":           wait_secs,
                    "queue_position_at_join": 1,
                    "abandoned":              False,
                    "zone_hotspot_x":         info["meta"].get("hotspot_x", 300.0),
                    "zone_hotspot_y":         info["meta"].get("hotspot_y", 200.0),
                    "gender":                 info["gender"],
                    "age":                    info["age"],
                    "age_bucket":             info["age_bucket"],
                })

        elif ev_upper == "ABANDONED":
            info = billing_joins.pop(visitor_id, None)
            if info:
                join_ts   = info["join_ts"]
                exit_ts   = timestamp
                wait_secs = max(0, int((exit_ts - join_ts).total_seconds()))
                output_events.append({
                    "queue_event_id":         str(event_id),
                    "event_type":             "queue_abandoned",
                    "track_id":               info["track_id"],
                    "store_id":               info["store_id"],
                    "camera_id":              info["camera_id"],
                    "zone_id":                "PURPLLE_MUM_1076_Z_BILLING_01",
                    "zone_name":              "Billing Counter Queue",
                    "zone_type":              "BILLING",
                    "is_revenue_zone":        "Yes",
                    "queue_join_ts":          join_ts.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                    "queue_served_ts":        None,
                    "queue_exit_ts":          timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                    "wait_seconds":           wait_secs,
                    "queue_position_at_join": 1,
                    "abandoned":              True,
                    "zone_hotspot_x":         info["meta"].get("hotspot_x", 300.0),
                    "zone_hotspot_y":         info["meta"].get("hotspot_y", 200.0),
                    "gender":                 info["gender"],
                    "age":                    info["age"],
                    "age_bucket":             info["age_bucket"],
                })

    conn.close()

    # ── Write JSONL ───────────────────────────────────────────────────────────
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for e in output_events:
            f.write(json.dumps(e) + "\n")

    entries   = sum(1 for e in output_events if e.get("event_type") == "entry" and not e.get("is_staff"))
    completed = sum(1 for e in output_events if e.get("event_type") == "queue_completed")
    abandoned = sum(1 for e in output_events if e.get("event_type") == "queue_abandoned")

    print()
    print("[OK] Exported %d events -> %s" % (len(output_events), OUTPUT_PATH))
    print("   Visitor entries : %d" % entries)
    print("   Queue completed : %d  |  Abandoned: %d" % (completed, abandoned))
    print()
    print("This file was generated from REAL video processing pipeline data.")
    print("Submit event_log.jsonl with your repository.")

if __name__ == "__main__":
    main()
