import os
import time
import datetime
import cv2
import numpy as np
from datetime import datetime, timezone
from detect import PersonDetector
from tracker import ByteTrackerWrapper
from reid import ReIDFeatureExtractor, ReIDMatcher
from staff_classifier import StaffClassifier
from event_generator import EventGenerator
from stream_producer import StreamProducer
from zone_classifier import ZoneClassifier

def main():
    store_id = "STORE_BLR_002"
    api_url = os.getenv("API_URL", "http://localhost:8000")
    
    print(f"Starting pipeline for store {store_id} pushing to {api_url}")
    
    # Initialize components
    detector = PersonDetector(model_path="yolov8s.pt")
    tracker = ByteTrackerWrapper()
    extractor = ReIDFeatureExtractor()
    matcher = ReIDMatcher()
    staff_classifier = StaffClassifier()
    event_gen = EventGenerator(store_id)
    producer = StreamProducer(api_url)
    zone_classifier = ZoneClassifier("/data/store_layout.json", store_id)
    
    # Video path
    video_path = "/data/CCTV Footage-20260529T160731Z-3-00144614ea/CCTV Footage/CAM 1.mp4"
    camera_id = "CAM_1"
    
    if not os.path.exists(video_path):
        print(f"Video file not found: {video_path}")
        return

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    
    # State tracking
    active_visitors = {} # visitor_id -> { 'last_zone': zone_id, 'entry_time': ts, 'last_seen': ts }
    
    print(f"Pipeline initialized. Ready to process frames from {video_path} at {fps} FPS.")
    
    frame_count = 0
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            # Process 3 out of every 5 frames (skip 2 max)
            if frame_count % 5 not in (0, 2, 4):
                continue
                
            current_time = datetime.now(timezone.utc)
            if frame_count % 30 == 0:
                print(f"Processing frame {frame_count}...")
                
            # 1. Detect
            detections = detector.detect(frame)
            
            # 2. Track
            tracked_objects = tracker.update(detections, frame)
            
            # Extract embeddings for current tracked objects
            if tracked_objects:
                boxes = [[t[0], t[1], t[2], t[3]] for t in tracked_objects]
                embeddings = extractor.extract(frame, boxes)
            else:
                embeddings = []

            for i, (x1, y1, x2, y2, local_track_id, conf) in enumerate(tracked_objects):
                bbox = [x1, y1, x2, y2]
                embedding = embeddings[i]
                
                # 3. Match ID
                visitor_id, is_reentry = matcher.match(camera_id, local_track_id, embedding, timestamp=current_time)
                
                # 4. Check Staff
                bbox_image = frame[int(max(0, y1)):int(y2), int(max(0, x1)):int(x2)]
                is_staff = staff_classifier.is_staff(local_track_id, None, 0, bbox_image=bbox_image)
                
                # 5. Zone Logic
                zone_id = zone_classifier.get_zone(bbox)
                sku_zone = zone_classifier.get_sku_zone(zone_id) if zone_id else None
                
                metadata = {"queue_depth": None, "sku_zone": sku_zone, "session_seq": 1}
                
                if visitor_id not in active_visitors:
                    # New visitor in this session run
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

            # Flush events to API batch
            producer.flush()
            
    except KeyboardInterrupt:
        print("Shutting down pipeline.")
    finally:
        producer.flush()
        cap.release()

if __name__ == "__main__":
    main()
