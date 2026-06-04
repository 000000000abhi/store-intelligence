#!/usr/bin/env python3
"""
generate_event_log.py — Generates a realistic JSONL event log in the exact schema
required by the Purplle Tech Challenge (matching sample_eventsbe42122.jsonl format).

Fixes:
  1. wait_seconds for abandoned queues = (queue_exit_ts - queue_join_ts).seconds
  2. Queue position is computed in a POST-PROCESSING pass over chronologically
     sorted billing events — never during sequential person generation.
  3. Both group members get their own entry/exit events.
  4. Store exit is ALWAYS after billing queue_exit_ts (temporal paradox fixed).
     Exit times are computed only after all billing events are known per person.

Usage:
    python scripts/generate_event_log.py
Output:
    event_log.jsonl  (in repo root)
"""

import json
import uuid
import random
from datetime import datetime, timedelta, timezone
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(REPO_ROOT, "event_log.jsonl")

random.seed(42)

STORE_ID    = "ST1076"
STORE_CODE  = "store_1076"
ENTRY_CAM   = "cam1"
ZONE_CAMS   = ["CAM2", "CAM3", "CAM4"]
BILLING_CAM = "PURPLLE_MUM_1076_CAM6"

ZONES = [
    {"zone_id": "PURPLLE_MUM_1076_Z01", "zone_name": "Left Shelf",       "zone_type": "SHELF",   "is_revenue_zone": "Yes"},
    {"zone_id": "PURPLLE_MUM_1076_Z02", "zone_name": "Center Display",   "zone_type": "DISPLAY", "is_revenue_zone": "Yes"},
    {"zone_id": "PURPLLE_MUM_1076_Z03", "zone_name": "Lipstick Aisle",   "zone_type": "SHELF",   "is_revenue_zone": "Yes"},
    {"zone_id": "PURPLLE_MUM_1076_Z04", "zone_name": "Skincare Section", "zone_type": "SHELF",   "is_revenue_zone": "Yes"},
    {"zone_id": "PURPLLE_MUM_1076_Z05", "zone_name": "Fragrance Corner", "zone_type": "SHELF",   "is_revenue_zone": "Yes"},
]
BILLING_ZONE = {
    "zone_id":         "PURPLLE_MUM_1076_Z_BILLING_01",
    "zone_name":       "Billing Counter Queue",
    "zone_type":       "BILLING",
    "is_revenue_zone": "Yes",
}

AGE_BUCKETS = {"18-24": (18, 24), "25-34": (25, 34), "35-44": (35, 44), "45-54": (45, 54)}
GENDERS     = ["F", "M", "F", "F", "M"]

BASE_TS      = datetime(2026, 3, 8, 10, 0, 0, tzinfo=timezone.utc)
NUM_VISITORS = 80
NUM_STAFF    = 4

events           = []
track_counter    = 100
id_token_counter = 60001
group_id_counter = 10

# Maps id_token -> latest known billing queue_exit_ts (datetime)
# Used to ensure store exit always happens AFTER billing is done.
person_billing_end = {}   # id_token -> datetime

def ts(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")

def rand_age_bucket():
    return random.choice(list(AGE_BUCKETS.keys()))

def rand_age(bucket):
    lo, hi = AGE_BUCKETS[bucket]
    return random.randint(lo, hi)

def rand_hotspot():
    return round(random.uniform(200, 700), 1), round(random.uniform(150, 400), 1)

def make_person():
    global id_token_counter, track_counter
    age_bucket = rand_age_bucket()
    p = {
        "id_token":       f"ID_{id_token_counter}",
        "track_id":       track_counter,
        "gender":         random.choice(GENDERS),
        "age_bucket":     age_bucket,
        "age":            rand_age(age_bucket),
        "is_face_hidden": random.random() < 0.05,
    }
    id_token_counter += 1
    track_counter    += 1
    return p

def make_entry(p, t, group_id=None, group_size=None):
    return {
        "event_type":      "entry",
        "id_token":        p["id_token"],
        "store_code":      STORE_CODE,
        "camera_id":       ENTRY_CAM,
        "event_timestamp": ts(t),
        "is_staff":        False,
        "gender_pred":     p["gender"],
        "age_pred":        p["age"],
        "age_bucket":      p["age_bucket"],
        "is_face_hidden":  p["is_face_hidden"],
        "group_id":        group_id,
        "group_size":      group_size,
    }

def make_exit(p, t, group_id=None, group_size=None):
    return {
        "event_type":      "exit",
        "id_token":        p["id_token"],
        "store_code":      STORE_CODE,
        "camera_id":       ENTRY_CAM,
        "event_timestamp": ts(t),
        "is_staff":        False,
        "gender_pred":     p["gender"],
        "age_pred":        p["age"],
        "age_bucket":      p["age_bucket"],
        "is_face_hidden":  p["is_face_hidden"],
        "group_id":        group_id,
        "group_size":      group_size,
    }

def make_zone_enter(p, cam, zone, t):
    hx, hy = rand_hotspot()
    return {
        "event_type":      "zone_entered",
        "track_id":        p["track_id"],
        "store_id":        STORE_ID,
        "camera_id":       cam,
        "zone_id":         zone["zone_id"],
        "zone_name":       zone["zone_name"],
        "zone_type":       zone["zone_type"],
        "is_revenue_zone": zone["is_revenue_zone"],
        "event_time":      ts(t),
        "zone_hotspot_x":  hx,
        "zone_hotspot_y":  hy,
        "gender":          p["gender"],
        "age":             p["age"],
        "age_bucket":      p["age_bucket"],
    }

def make_zone_exit(p, cam, zone, t, hx, hy):
    return {
        "event_type":      "zone_exited",
        "track_id":        p["track_id"],
        "store_id":        STORE_ID,
        "camera_id":       cam,
        "zone_id":         zone["zone_id"],
        "zone_name":       zone["zone_name"],
        "zone_type":       zone["zone_type"],
        "is_revenue_zone": zone["is_revenue_zone"],
        "event_time":      ts(t),
        "zone_hotspot_x":  round(hx + random.uniform(-5, 5), 1),
        "zone_hotspot_y":  round(hy + random.uniform(-5, 5), 1),
        "gender":          p["gender"],
        "age":             p["age"],
        "age_bucket":      p["age_bucket"],
    }

def make_billing_event(p, queue_join_dt, abandoned):
    """
    Build a billing event.
    wait_seconds is always computed from the actual timestamps (FIX 1).
    queue_position_at_join is set to 0 here — it will be fixed in the
    post-processing pass AFTER all events are sorted (FIX 2).
    """
    if abandoned:
        actual_wait  = random.randint(60, 300)
        queue_exit_dt = queue_join_dt + timedelta(seconds=actual_wait)
        wait_seconds  = actual_wait          # FIX 1: real elapsed time
        served_ts_val = None
    else:
        wait_secs     = random.randint(5, 120)
        queue_served_dt = queue_join_dt + timedelta(seconds=wait_secs)
        service_secs  = random.randint(60, 300)
        queue_exit_dt = queue_served_dt + timedelta(seconds=service_secs)
        wait_seconds  = wait_secs            # FIX 1: serve_ts - join_ts
        served_ts_val = ts(queue_served_dt)

    hx, hy = rand_hotspot()
    event = {
        "queue_event_id":         str(uuid.uuid4()),
        "event_type":             "queue_abandoned" if abandoned else "queue_completed",
        "track_id":               p["track_id"],
        "store_id":               STORE_ID,
        "camera_id":              BILLING_CAM,
        "zone_id":                BILLING_ZONE["zone_id"],
        "zone_name":              BILLING_ZONE["zone_name"],
        "zone_type":              BILLING_ZONE["zone_type"],
        "is_revenue_zone":        BILLING_ZONE["is_revenue_zone"],
        "queue_join_ts":          ts(queue_join_dt),
        "queue_served_ts":        served_ts_val,
        "queue_exit_ts":          ts(queue_exit_dt),
        "wait_seconds":           wait_seconds,
        "queue_position_at_join": 0,   # placeholder — fixed in post-processing
        "abandoned":              abandoned,
        "zone_hotspot_x":         hx,
        "zone_hotspot_y":         hy,
        "gender":                 p["gender"],
        "age":                    p["age"],
        "age_bucket":             p["age_bucket"],
        # internal helper fields — removed before writing
        "_id_token":              p["id_token"],
        "_queue_exit_dt":         queue_exit_dt,
    }
    return event, queue_exit_dt


# ─── 1. Staff entries ─────────────────────────────────────────────────────────
for s_idx in range(NUM_STAFF):
    t = BASE_TS + timedelta(seconds=random.randint(10, 180))
    events.append({
        "event_type":      "entry",
        "id_token":        f"STAFF_{1001 + s_idx}",
        "store_code":      STORE_CODE,
        "camera_id":       ENTRY_CAM,
        "event_timestamp": ts(t),
        "is_staff":        True,
        "gender_pred":     random.choice(["F", "M"]),
        "age_pred":        random.randint(22, 40),
        "age_bucket":      "25-34",
        "is_face_hidden":  False,
        "group_id":        None,
        "group_size":      None,
    })


# ─── 2. Visitor journeys ──────────────────────────────────────────────────────
visitor_start_offset = 60

for v_idx in range(NUM_VISITORS):
    is_group_lead = random.random() < 0.25 and v_idx < NUM_VISITORS - 1
    group_id   = None
    group_size = None
    if is_group_lead:
        group_id   = f"G_{group_id_counter}"
        group_size = 2
        group_id_counter += 1

    person1    = make_person()
    entry_time1 = BASE_TS + timedelta(seconds=visitor_start_offset)
    visitor_start_offset += random.randint(15, 90)

    person2     = make_person() if is_group_lead else None
    entry_time2 = entry_time1 + timedelta(seconds=random.randint(1, 8)) if is_group_lead else None

    # -- ENTRY --
    events.append(make_entry(person1, entry_time1, group_id, group_size))
    if is_group_lead:
        events.append(make_entry(person2, entry_time2, group_id, group_size))

    # -- ZONE VISITS --
    current_time = entry_time1 + timedelta(seconds=random.randint(10, 60))
    visited_zones = random.sample(ZONES, k=random.randint(1, 3))

    for z in visited_zones:
        cam = random.choice(ZONE_CAMS)
        hx, hy = rand_hotspot()
        ze_time  = current_time
        dwell    = random.randint(20, 180)
        zx_time  = ze_time + timedelta(seconds=dwell)

        events.append(make_zone_enter(person1, cam, z, ze_time))
        events.append(make_zone_exit(person1, cam, z, zx_time, hx, hy))

        if is_group_lead:
            hx2, hy2 = rand_hotspot()
            off = timedelta(seconds=random.randint(2, 10))
            events.append(make_zone_enter(person2, cam, z, ze_time + off))
            events.append(make_zone_exit(person2, cam, z, zx_time + off, hx2, hy2))

        current_time = zx_time + timedelta(seconds=random.randint(5, 30))

    # -- BILLING --
    goes_to_billing = random.random() < 0.60
    billing_end1 = None

    if goes_to_billing:
        abandoned = random.random() < 0.15
        billing_evt, billing_end1 = make_billing_event(person1, current_time, abandoned)
        events.append(billing_evt)
        # Register this person's billing end for exit-time clamping
        person_billing_end[person1["id_token"]] = billing_end1

        if is_group_lead and random.random() < 0.7:
            join2     = current_time + timedelta(seconds=random.randint(2, 15))
            abandoned2 = random.random() < 0.15
            billing_evt2, billing_end2 = make_billing_event(person2, join2, abandoned2)
            events.append(billing_evt2)
            person_billing_end[person2["id_token"]] = billing_end2

    # -- EXIT (FIX 4: clamp exit to AFTER billing end) --
    raw_exit1 = current_time + timedelta(seconds=random.randint(10, 60))
    # If person went to billing, exit must be after billing_end1
    if billing_end1 is not None:
        raw_exit1 = max(raw_exit1, billing_end1 + timedelta(seconds=random.randint(10, 60)))

    events.append(make_exit(person1, raw_exit1, group_id, group_size))

    if is_group_lead:
        billing_end2 = person_billing_end.get(person2["id_token"])
        raw_exit2 = raw_exit1 + timedelta(seconds=random.randint(1, 30))
        if billing_end2 is not None:
            raw_exit2 = max(raw_exit2, billing_end2 + timedelta(seconds=random.randint(10, 60)))
        events.append(make_exit(person2, raw_exit2, group_id, group_size))

    visitor_start_offset += random.randint(0, 30)


# ─── 3. Sort all events chronologically ──────────────────────────────────────
def sort_key(e):
    for k in ("event_timestamp", "event_time", "queue_join_ts"):
        if k in e and e[k]:
            return e[k]
    return ""

events.sort(key=sort_key)


# ─── 4. POST-PROCESSING: Fix queue positions (FIX 2) ─────────────────────────
# Now that all events are chronologically sorted, iterate billing events
# in join-time order and compute real concurrent queue depth at each join.
billing_events = [e for e in events if e.get("event_type") in ("queue_completed", "queue_abandoned")]
billing_events.sort(key=lambda e: e["queue_join_ts"])

for i, bev in enumerate(billing_events):
    join_dt  = datetime.fromisoformat(bev["queue_join_ts"].replace("Z", "+00:00"))
    exit_dt  = datetime.fromisoformat(bev["queue_exit_ts"].replace("Z", "+00:00"))
    # Count how many EARLIER billing events still have people in queue at join_dt
    depth = sum(
        1
        for prev in billing_events[:i]
        if datetime.fromisoformat(prev["queue_exit_ts"].replace("Z", "+00:00")) > join_dt
    )
    bev["queue_position_at_join"] = depth + 1   # 1-indexed


# ─── 5. Strip internal helper fields ─────────────────────────────────────────
for e in events:
    e.pop("_id_token",       None)
    e.pop("_queue_exit_dt",  None)


# ─── 6. Write JSONL ───────────────────────────────────────────────────────────
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    for e in events:
        f.write(json.dumps(e) + "\n")

total_entries  = sum(1 for e in events if e.get("event_type") == "entry" and not e.get("is_staff"))
total_abandon  = sum(1 for e in events if e.get("event_type") == "queue_abandoned")
total_complete = sum(1 for e in events if e.get("event_type") == "queue_completed")

print("[OK] Generated %d events -> %s" % (len(events), OUTPUT_PATH))
print("   Visitor entries : %d" % total_entries)
print("   Queue completed : %d  |  Abandoned: %d" % (total_complete, total_abandon))
print("   Staff (excluded): %d" % NUM_STAFF)
print("   Store: %s" % STORE_ID)
