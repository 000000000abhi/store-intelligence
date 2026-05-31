import numpy as np
import cv2

class ReIDFeatureExtractor:
    def __init__(self, model_name="hsv_fallback"):
        self.model_name = model_name

    def extract(self, frame, boxes):
        embeddings = []
        for box in boxes:
            x1, y1, x2, y2 = map(int, box)
            # Ensure within frame bounds
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(frame.shape[1], x2)
            y2 = min(frame.shape[0], y2)
            
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                embeddings.append(np.zeros(96))
                continue
                
            # Extract HSV histogram (96 dimensions: 32 bins per channel)
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            hist_h = cv2.calcHist([hsv], [0], None, [32], [0, 180])
            hist_s = cv2.calcHist([hsv], [1], None, [32], [0, 256])
            hist_v = cv2.calcHist([hsv], [2], None, [32], [0, 256])
            
            # Concatenate and normalize
            feature = np.concatenate([hist_h, hist_s, hist_v]).flatten()
            norm = np.linalg.norm(feature)
            if norm > 0:
                feature = feature / norm
                
            embeddings.append(feature)
            
        return embeddings

class ReIDMatcher:
    def __init__(self, threshold=0.82):
        self.threshold = threshold
        self.global_gallery = {} # global_visitor_id -> embedding
        self.camera_track_to_global = {} # (camera_id, local_track_id) -> global_visitor_id
        self.exit_history = [] # list of dicts: {'visitor_id': id, 'embedding': emb, 'timestamp': ts}
        import uuid
        self.uuid_gen = uuid.uuid4

    def match(self, camera_id, track_id, embedding, timestamp=None):
        cache_key = f"{camera_id}_{track_id}"
        if cache_key in self.camera_track_to_global:
            return self.camera_track_to_global[cache_key], False # existing, not a reentry

        best_match_id = None
        best_sim = -1
        is_reentry = False
        
        # 1. Check existing global gallery
        for vid, ref_emb in self.global_gallery.items():
            sim = np.dot(embedding, ref_emb)
            if sim > best_sim and sim >= self.threshold:
                best_sim = sim
                best_match_id = vid
                
        # 2. Check recent EXITS for REENTRY (15 min window)
        if not best_match_id and timestamp:
            from datetime import timedelta
            fifteen_mins_ago = timestamp - timedelta(minutes=15)
            # Cleanup old exits
            self.exit_history = [e for e in self.exit_history if e['timestamp'] >= fifteen_mins_ago]
            
            for exit_record in self.exit_history:
                sim = np.dot(embedding, exit_record['embedding'])
                if sim > best_sim and sim >= self.threshold:
                    best_sim = sim
                    best_match_id = exit_record['visitor_id']
                    is_reentry = True

        if best_match_id:
            self.camera_track_to_global[cache_key] = best_match_id
            # Blend embedding
            self.global_gallery[best_match_id] = 0.8 * self.global_gallery[best_match_id] + 0.2 * embedding
            self.global_gallery[best_match_id] /= np.linalg.norm(self.global_gallery[best_match_id])
            return best_match_id, is_reentry
            
        # 3. New visitor
        new_vid = f"VIS_{str(self.uuid_gen())[:6]}"
        self.global_gallery[new_vid] = embedding
        self.camera_track_to_global[cache_key] = new_vid
        
        return new_vid, False
        
    def record_exit(self, visitor_id, timestamp):
        if visitor_id in self.global_gallery:
            self.exit_history.append({
                'visitor_id': visitor_id,
                'embedding': self.global_gallery[visitor_id],
                'timestamp': timestamp
            })
