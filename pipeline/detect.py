import cv2
from ultralytics import YOLO

class PersonDetector:
    def __init__(self, model_path="yolov8s.pt", conf_threshold=0.5):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold

    def detect(self, frame):
        # Run YOLOv8 on frame
        # Filter for class 0 (person)
        # Return bounding boxes and confidences
        results = self.model(frame, classes=[0], conf=self.conf_threshold, verbose=False)
        detections = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = box.conf[0].cpu().item()
                detections.append(([x1, y1, x2, y2], conf))
        return detections
