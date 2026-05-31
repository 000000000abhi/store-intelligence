import cv2
import numpy as np

class StaffClassifier:
    def __init__(self, employee_roster=None):
        self.employee_roster = employee_roster or []
        # Reference uniform color (e.g. purple/black)
        self.reference_hist_h = None
        self.reference_hist_s = None
        
    def calibrate(self, reference_image):
        hsv = cv2.cvtColor(reference_image, cv2.COLOR_BGR2HSV)
        self.reference_hist_h = cv2.calcHist([hsv], [0], None, [32], [0, 180])
        self.reference_hist_s = cv2.calcHist([hsv], [1], None, [32], [0, 256])
        cv2.normalize(self.reference_hist_h, self.reference_hist_h, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        cv2.normalize(self.reference_hist_s, self.reference_hist_s, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

    def is_staff(self, track_id, zone_id, dwell_time, bbox_image=None):
        if bbox_image is None or self.reference_hist_h is None:
            return False
            
        # Focus on upper body (top 50% of bbox) for uniform
        h, w = bbox_image.shape[:2]
        upper_body = bbox_image[0:h//2, 0:w]
        
        if upper_body.size == 0:
            return False
            
        hsv = cv2.cvtColor(upper_body, cv2.COLOR_BGR2HSV)
        hist_h = cv2.calcHist([hsv], [0], None, [32], [0, 180])
        hist_s = cv2.calcHist([hsv], [1], None, [32], [0, 256])
        cv2.normalize(hist_h, hist_h, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        cv2.normalize(hist_s, hist_s, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        
        sim_h = cv2.compareHist(self.reference_hist_h, hist_h, cv2.HISTCMP_CORREL)
        sim_s = cv2.compareHist(self.reference_hist_s, hist_s, cv2.HISTCMP_CORREL)
        
        # If color profile matches > 60%, flag as staff
        return (sim_h > 0.6) and (sim_s > 0.6)
