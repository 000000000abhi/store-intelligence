import os
import time
import datetime
import cv2
import numpy as np
from datetime import datetime, timezone
import argparse
import glob

from detect import PersonDetector
from tracker import ByteTrackerWrapper
from reid import ReIDFeatureExtractor, ReIDMatcher
from staff_classifier import StaffClassifier
from event_generator import EventGenerator
from stream_producer import StreamProducer
from zone_classifier import ZoneClassifier

def process_video(video_path, camera_id, store_id, api_url):
    print(f"\n{'='*50}\nStarting pipeline for {store_id} ({camera_id})\nVideo: {video_path}\n{'='*50}")
    
    detector = PersonDetector(model_path="yolov8s.pt")
    tracker = ByteTrackerWrapper()
    extractor = ReIDFeatureExtractor()
    matcher = ReIDMatcher()
    staff_classifier = StaffClassifier()
    event_gen = EventGenerator(store_id)
    producer = StreamProducer(api_url)
    zone_classifier = ZoneClassifier("/data/store_layout.json", store_id)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    
    active_visitors = {}
    
    print(f"Ready to process frames from {video_path} at {fps} FPS.")
    
    frame_count = 0
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            if frame_count % 5 not in (0, 2, 4):
                continue
                
            current_time = datetime.now(timezone.utc)
            if frame_count % 30 == 0:
                print(f"[{camera_id}] Processing frame {frame_count}...")
                
            detections = detector.detect(frame)
            tracked_objects = tracker.update(detections, frame)
            
            if tracked_objects:
                boxes = [[t[0], t[1], t[2], t[3]] for t in tracked_objects]
                embeddings = extractor.extract(frame, boxes)
            else:
                embeddings = []

            for i, (x1, y1, x2, y2, local_track_id, conf) in enumerate(tracked_objects):
                bbox = [x1, y1, x2, y2]
                embedding = embeddings[i]
                
                visitor_id, is_reentry = matcher.match(camera_id, local_track_id, embedding, timestamp=current_time)
                
                bbox_image = frame[int(max(0, y1)):int(y2), int(max(0, x1)):int(x2)]
                is_staff = staff_classifier.is_staff(local_track_id, None, 0, bbox_image=bbox_image)
                
                zone_id = zone_classifier.get_zone(bbox)
                
                # Fallback to filename-based zone classification if JSON is missing
                if not zone_id:
                    if "billing" in video_path.lower():
                        zone_id = "BILLING"
                    elif "zone" in video_path.lower():
                        zone_id = "ZONE"
                    else:
                        zone_id = None
                        
                sku_zone = zone_classifier.get_sku_zone(zone_id) if zone_id else None
                
                metadata = {"queue_depth": None, "sku_zone": sku_zone, "session_seq": 1}
                
                if visitor_id not in active_visitors:
                    event_type = "REENTRY" if is_reentry else "ENTRY"
                    event = event_gen._build_event(
                        camera_id, visitor_id, event_type, current_time,
                        zone_id=None, is_staff=is_staff, metadata=metadata
                    )
                    event["confidence"] = conf
                    producer.push(event)
                    active_visitors[visitor_id] = {
                        'last_zone': None,
                        'entry_time': current_time,
                        'last_seen': current_time
                    }
                    
                state = active_visitors[visitor_id]
                state['last_seen'] = current_time
                
                if zone_id and zone_id != state['last_zone']:
                    event_type = "BILLING_QUEUE_JOIN" if zone_id == "BILLING" else "ZONE_ENTER"
                    event = event_gen._build_event(
                        camera_id, visitor_id, event_type, current_time,
                        zone_id=zone_id, is_staff=is_staff, metadata=metadata
                    )
                    event["confidence"] = conf
                    producer.push(event)
                    state['last_zone'] = zone_id

            producer.flush()
            
    except KeyboardInterrupt:
        print("Shutting down pipeline.")
        raise
    finally:
        producer.flush()
        cap.release()
        print(f"Finished processing {video_path}\n")


def main():
    parser = argparse.ArgumentParser(description="Store Intelligence CV Pipeline")
    parser.add_argument("--auto", action="store_true", help="Automatically find and process all MP4s in /data")
    parser.add_argument("--video", type=str, help="Path to specific video file")
    parser.add_argument("--camera-id", type=str, help="Camera ID (e.g. CAM_1)")
    parser.add_argument("--store-id", type=str, help="Store ID (e.g. ST1076)")
    args = parser.parse_args()
    
    api_url = os.getenv("API_URL", "http://localhost:8000")
    
    if args.auto or (not args.video):
        print("Auto-discovery mode activated. Searching for videos in /data...")
        video_files = glob.glob("/data/**/*.mp4", recursive=True)
        if not video_files:
            print("No .mp4 files found in /data directory.")
            return
            
        for video_path in video_files:
            filename = os.path.basename(video_path)
            camera_id = filename.split(" -")[0].replace(" ", "_").upper()
            
            if "Store 1" in video_path:
                store_id = "ST1001"
            elif "Store 2" in video_path:
                store_id = "ST1002"
            else:
                store_id = "ST_UNKNOWN"
                
            process_video(video_path, camera_id, store_id, api_url)
            
    else:
        if not all([args.video, args.camera_id, args.store_id]):
            print("Error: In manual mode, --video, --camera-id, and --store-id are all required.")
            return
            
        if not os.path.exists(args.video):
            print(f"Video file not found: {args.video}")
            return
            
        process_video(args.video, args.camera_id, args.store_id, api_url)

if __name__ == "__main__":
    main()
