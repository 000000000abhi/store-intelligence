class ByteTrackerWrapper:
    def __init__(self, track_thresh=0.5, track_buffer=30, match_thresh=0.8):
        import supervision as sv
        # Handle library version differences
        TrackerClass = getattr(sv, "ByteTrack", None) or getattr(sv, "ByteTracker")
        try:
            self.tracker = TrackerClass()
        except TypeError:
            self.tracker = TrackerClass(track_thresh=track_thresh, track_buffer=track_buffer, match_thresh=match_thresh)

    def update(self, detections, frame):
        import supervision as sv
        
        # Convert YOLO detections to supervision Detections object
        if not detections:
            return []
            
        boxes = []
        confidences = []
        for bbox, conf in detections:
            boxes.append(bbox)
            confidences.append(conf)
            
        import numpy as np
        sv_detections = sv.Detections(
            xyxy=np.array(boxes),
            confidence=np.array(confidences),
            class_id=np.zeros(len(boxes), dtype=int)
        )
        
        tracked_detections = self.tracker.update_with_detections(sv_detections)
        
        results = []
        for i in range(len(tracked_detections)):
            bbox = tracked_detections.xyxy[i].tolist()
            conf = tracked_detections.confidence[i]
            track_id = tracked_detections.tracker_id[i]
            results.append([bbox[0], bbox[1], bbox[2], bbox[3], track_id, conf])
            
        return results
