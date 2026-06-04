import os
import json
import cv2
import numpy as np
from datetime import datetime, timezone
import argparse
import glob
import uuid

from detect import PersonDetector
from tracker import ByteTrackerWrapper
from reid import ReIDFeatureExtractor, ReIDMatcher
from staff_classifier import StaffClassifier
from event_generator import EventGenerator
from stream_producer import StreamProducer
from zone_classifier import ZoneClassifier

# ── JSONL writer — formats pipeline events into the challenge schema ──────────
class EventLogWriter:
    """
    Writes events detected from real video to a JSONL file in the exact
    schema required by the Purplle Tech Challenge (matching sample_eventsbe42122.jsonl).
    One JSON object per line, flushed immediately so the file is always readable.
    """
    ZONE_META = {
        "BILLING": {
            "zone_id":   "PURPLLE_MUM_1076_Z_BILLING_01",
            "zone_name": "Billing Counter Queue",
            "zone_type": "BILLING",
        },
        "ZONE": {
            "zone_id":   "PURPLLE_MUM_1076_Z01",
            "zone_name": "General Floor Zone",
            "zone_type": "SHELF",
        },
    }

    def __init__(self, output_path, store_code):
        self.output_path = output_path
        self.store_code  = store_code
        self._f = open(output_path, "a", encoding="utf-8")
        # per-visitor tracking for billing dwell
        self._billing_join = {}     # visitor_id -> join datetime
        self._visitor_counter = {}  # visitor_id -> short numeric token

    def _id_token(self, visitor_id):
        if visitor_id not in self._visitor_counter:
            self._visitor_counter[visitor_id] = 60000 + len(self._visitor_counter) + 1
        return "ID_%d" % self._visitor_counter[visitor_id]

    def write_entry(self, visitor_id, camera_id, timestamp, is_staff,
                    gender=None, age=None, age_bucket=None):
        rec = {
            "event_type":      "entry" if not is_staff else "entry",
            "id_token":        visitor_id if is_staff else self._id_token(visitor_id),
            "store_code":      self.store_code,
            "camera_id":       camera_id,
            "event_timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "is_staff":        is_staff,
            "gender_pred":     gender,
            "age_pred":        age,
            "age_bucket":      age_bucket,
            "is_face_hidden":  False,
            "group_id":        None,
            "group_size":      None,
        }
        self._write(rec)

    def write_exit(self, visitor_id, camera_id, timestamp, is_staff,
                   gender=None, age=None, age_bucket=None):
        rec = {
            "event_type":      "exit",
            "id_token":        visitor_id if is_staff else self._id_token(visitor_id),
            "store_code":      self.store_code,
            "camera_id":       camera_id,
            "event_timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "is_staff":        is_staff,
            "gender_pred":     gender,
            "age_pred":        age,
            "age_bucket":      age_bucket,
            "is_face_hidden":  False,
            "group_id":        None,
            "group_size":      None,
        }
        self._write(rec)

    def write_zone_enter(self, visitor_id, track_id, store_id, camera_id,
                         zone_id, zone_name, zone_type, timestamp,
                         hotspot_x, hotspot_y, gender=None, age=None, age_bucket=None):
        rec = {
            "event_type":      "zone_entered",
            "track_id":        track_id,
            "store_id":        store_id,
            "camera_id":       camera_id,
            "zone_id":         zone_id,
            "zone_name":       zone_name,
            "zone_type":       zone_type,
            "is_revenue_zone": "Yes",
            "event_time":      timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "zone_hotspot_x":  round(hotspot_x, 1),
            "zone_hotspot_y":  round(hotspot_y, 1),
            "gender":          gender,
            "age":             age,
            "age_bucket":      age_bucket,
        }
        self._write(rec)

    def write_zone_exit(self, visitor_id, track_id, store_id, camera_id,
                        zone_id, zone_name, zone_type, timestamp,
                        hotspot_x, hotspot_y, gender=None, age=None, age_bucket=None):
        rec = {
            "event_type":      "zone_exited",
            "track_id":        track_id,
            "store_id":        store_id,
            "camera_id":       camera_id,
            "zone_id":         zone_id,
            "zone_name":       zone_name,
            "zone_type":       zone_type,
            "is_revenue_zone": "Yes",
            "event_time":      timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "zone_hotspot_x":  round(hotspot_x, 1),
            "zone_hotspot_y":  round(hotspot_y, 1),
            "gender":          gender,
            "age":             age,
            "age_bucket":      age_bucket,
        }
        self._write(rec)

    def write_billing_join(self, visitor_id, track_id, store_id, camera_id,
                           timestamp, hotspot_x, hotspot_y,
                           gender=None, age=None, age_bucket=None):
        """Record billing join time — the full event is written on exit."""
        self._billing_join[visitor_id] = {
            "join_ts":    timestamp,
            "track_id":   track_id,
            "store_id":   store_id,
            "camera_id":  camera_id,
            "hotspot_x":  hotspot_x,
            "hotspot_y":  hotspot_y,
            "gender":     gender,
            "age":        age,
            "age_bucket": age_bucket,
        }

    def write_billing_exit(self, visitor_id, exit_ts, abandoned=False):
        """Write a complete queue_completed / queue_abandoned event."""
        info = self._billing_join.pop(visitor_id, None)
        if not info:
            return
        join_ts   = info["join_ts"]
        wait_secs = max(0, int((exit_ts - join_ts).total_seconds()))
        bz        = self.ZONE_META["BILLING"]
        rec = {
            "queue_event_id":         str(uuid.uuid4()),
            "event_type":             "queue_abandoned" if abandoned else "queue_completed",
            "track_id":               info["track_id"],
            "store_id":               info["store_id"],
            "camera_id":              info["camera_id"],
            "zone_id":                bz["zone_id"],
            "zone_name":              bz["zone_name"],
            "zone_type":              bz["zone_type"],
            "is_revenue_zone":        "Yes",
            "queue_join_ts":          join_ts.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "queue_served_ts":        None if abandoned else exit_ts.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "queue_exit_ts":          exit_ts.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "wait_seconds":           wait_secs,
            "queue_position_at_join": 1,   # approximated; accurate version needs global state
            "abandoned":              abandoned,
            "zone_hotspot_x":         round(info["hotspot_x"], 1),
            "zone_hotspot_y":         round(info["hotspot_y"], 1),
            "gender":                 info["gender"],
            "age":                    info["age"],
            "age_bucket":             info["age_bucket"],
        }
        self._write(rec)

    def _write(self, record):
        self._f.write(json.dumps(record) + "\n")
        self._f.flush()

    def close(self):
        self._f.close()


# ── Pipeline ──────────────────────────────────────────────────────────────────
def process_video(video_path, camera_id, store_id, api_url, log_writer=None):
    store_code = store_id.lower().replace("st", "store_")   # ST1076 -> store_1076
    print("\n" + "="*50)
    print("Starting pipeline for %s (%s)" % (store_id, camera_id))
    print("Video: %s" % video_path)
    print("="*50)

    detector        = PersonDetector(model_path="yolov8s.pt")
    tracker         = ByteTrackerWrapper()
    extractor       = ReIDFeatureExtractor()
    matcher         = ReIDMatcher()
    staff_classifier = StaffClassifier()
    event_gen       = EventGenerator(store_id)
    producer        = StreamProducer(api_url)
    zone_classifier = ZoneClassifier("/data/store_layout.json", store_id)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0

    # Determine zone type hint from filename
    fname = os.path.basename(video_path).lower()
    if "billing" in fname:
        cam_zone_hint = "BILLING"
    elif "entry" in fname:
        cam_zone_hint = "ENTRY"
    else:
        cam_zone_hint = "ZONE"

    active_visitors = {}  # visitor_id -> {last_zone, entry_time, last_seen, track_id}
    frame_count = 0

    print("Ready to process at %.1f FPS. Zone hint: %s" % (fps, cam_zone_hint))

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            if frame_count % 5 not in (0, 2, 4):
                continue

            current_time = datetime.now(timezone.utc)
            if frame_count % 150 == 0:
                print("[%s] Frame %d..." % (camera_id, frame_count))

            detections     = detector.detect(frame)
            tracked_objects = tracker.update(detections, frame)

            if tracked_objects:
                boxes      = [[t[0], t[1], t[2], t[3]] for t in tracked_objects]
                embeddings = extractor.extract(frame, boxes)
            else:
                embeddings = []

            for i, (x1, y1, x2, y2, local_track_id, conf) in enumerate(tracked_objects):
                bbox       = [x1, y1, x2, y2]
                embedding  = embeddings[i]
                hotspot_x  = (x1 + x2) / 2.0
                hotspot_y  = y2   # feet position

                visitor_id, is_reentry = matcher.match(
                    camera_id, local_track_id, embedding, timestamp=current_time)

                bbox_image = frame[int(max(0, y1)):int(y2), int(max(0, x1)):int(x2)]
                is_staff   = staff_classifier.is_staff(
                    local_track_id, None, 0, bbox_image=bbox_image)

                # Zone determination (filename fallback if no layout JSON)
                zone_id = zone_classifier.get_zone(bbox)
                if not zone_id:
                    if cam_zone_hint == "BILLING":
                        zone_id = "BILLING"
                    elif cam_zone_hint == "ENTRY":
                        zone_id = None  # entry cam — just count footfall
                    else:
                        zone_id = "ZONE"

                # Build zone metadata
                zone_meta = {
                    "zone_id":   "PURPLLE_MUM_1076_Z_BILLING_01" if zone_id == "BILLING" else "PURPLLE_MUM_1076_Z01",
                    "zone_name": "Billing Counter Queue"         if zone_id == "BILLING" else "General Floor Zone",
                    "zone_type": "BILLING"                       if zone_id == "BILLING" else "SHELF",
                }

                # ── State machine ─────────────────────────────────────────────
                if visitor_id not in active_visitors:
                    event_type = "REENTRY" if is_reentry else "ENTRY"
                    event = event_gen._build_event(
                        camera_id, visitor_id, event_type, current_time,
                        zone_id=None, is_staff=is_staff)
                    event["confidence"] = conf
                    producer.push(event)

                    # Write to JSONL
                    if log_writer and not is_staff:
                        log_writer.write_entry(
                            visitor_id, camera_id, current_time, is_staff=False)

                    active_visitors[visitor_id] = {
                        "last_zone":  None,
                        "entry_time": current_time,
                        "last_seen":  current_time,
                        "track_id":   local_track_id,
                    }

                state = active_visitors[visitor_id]
                state["last_seen"] = current_time
                state["track_id"]  = local_track_id

                if zone_id and zone_id != state["last_zone"]:
                    if zone_id == "BILLING":
                        event_type = "BILLING_QUEUE_JOIN"
                        if log_writer and not is_staff:
                            log_writer.write_billing_join(
                                visitor_id, local_track_id, store_id, camera_id,
                                current_time, hotspot_x, hotspot_y)
                    else:
                        event_type = "ZONE_ENTER"
                        if log_writer and not is_staff:
                            log_writer.write_zone_enter(
                                visitor_id, local_track_id, store_id, camera_id,
                                zone_meta["zone_id"], zone_meta["zone_name"],
                                zone_meta["zone_type"], current_time,
                                hotspot_x, hotspot_y)

                    # Previous zone exit
                    if state["last_zone"] and log_writer and not is_staff:
                        prev_meta = {
                            "zone_id":   "PURPLLE_MUM_1076_Z_BILLING_01" if state["last_zone"] == "BILLING" else "PURPLLE_MUM_1076_Z01",
                            "zone_name": "Billing Counter Queue"          if state["last_zone"] == "BILLING" else "General Floor Zone",
                            "zone_type": "BILLING"                        if state["last_zone"] == "BILLING" else "SHELF",
                        }
                        if state["last_zone"] == "BILLING":
                            log_writer.write_billing_exit(visitor_id, current_time, abandoned=False)
                        else:
                            log_writer.write_zone_exit(
                                visitor_id, local_track_id, store_id, camera_id,
                                prev_meta["zone_id"], prev_meta["zone_name"],
                                prev_meta["zone_type"], current_time,
                                hotspot_x, hotspot_y)

                    event = event_gen._build_event(
                        camera_id, visitor_id, event_type, current_time,
                        zone_id=zone_id, is_staff=is_staff)
                    event["confidence"] = conf
                    producer.push(event)
                    state["last_zone"] = zone_id

            producer.flush()

    except KeyboardInterrupt:
        print("Interrupted — flushing final events.")
    finally:
        # Write exit events for everyone still in the store
        for vid, state in active_visitors.items():
            if log_writer:
                log_writer.write_exit(vid, camera_id, state["last_seen"], is_staff=False)
                if state["last_zone"] == "BILLING":
                    log_writer.write_billing_exit(vid, state["last_seen"], abandoned=True)
        producer.flush()
        cap.release()
        print("Finished: %s" % video_path)


def main():
    parser = argparse.ArgumentParser(description="Store Intelligence CV Pipeline")
    parser.add_argument("--auto",       action="store_true", help="Auto-discover all MP4s in /data")
    parser.add_argument("--video",      type=str, help="Path to specific video")
    parser.add_argument("--camera-id",  type=str, help="Camera ID (e.g. CAM_1)")
    parser.add_argument("--store-id",   type=str, help="Store ID (e.g. ST1076)")
    parser.add_argument("--output-log", type=str, default="/data/event_log.jsonl",
                        help="Path to write JSONL event log (default: /data/event_log.jsonl)")
    args = parser.parse_args()

    api_url = os.getenv("API_URL", "http://localhost:8000")

    # Single shared log writer for all videos so the log accumulates
    log_writer = EventLogWriter(args.output_log, store_code="store_1076")
    print("Writing real event log to: %s" % args.output_log)

    if args.auto or (not args.video):
        print("Auto-discovery mode — scanning /data for .mp4 files...")
        video_files = glob.glob("/data/**/*.mp4", recursive=True)
        if not video_files:
            print("No .mp4 files found in /data")
            log_writer.close()
            return

        for video_path in sorted(video_files):
            filename  = os.path.basename(video_path)
            camera_id = filename.split(" -")[0].replace(" ", "_").upper()
            store_id  = "ST1001" if "Store 1" in video_path else "ST1002"
            process_video(video_path, camera_id, store_id, api_url, log_writer)

    else:
        if not all([args.video, args.camera_id, args.store_id]):
            print("Error: --video, --camera-id, and --store-id are all required in manual mode.")
            log_writer.close()
            return
        if not os.path.exists(args.video):
            print("Video not found: %s" % args.video)
            log_writer.close()
            return
        process_video(args.video, args.camera_id, args.store_id, api_url, log_writer)

    log_writer.close()
    print("\nEvent log written to: %s" % args.output_log)
    print("Copy this file to the repo root as event_log.jsonl before submitting.")

if __name__ == "__main__":
    main()
