import uuid
from datetime import datetime

class EventGenerator:
    def __init__(self, store_id):
        self.store_id = store_id

    def generate_entry_event(self, camera_id, visitor_id, is_staff, timestamp):
        return self._build_event(camera_id, visitor_id, "ENTRY", timestamp, is_staff=is_staff)

    def generate_exit_event(self, camera_id, visitor_id, is_staff, timestamp):
        return self._build_event(camera_id, visitor_id, "EXIT", timestamp, is_staff=is_staff)

    def generate_zone_event(self, camera_id, visitor_id, event_type, zone_id, dwell_ms, is_staff, timestamp):
        event = self._build_event(camera_id, visitor_id, event_type, timestamp, zone_id=zone_id, dwell_ms=dwell_ms, is_staff=is_staff)
        return event

    def _build_event(self, camera_id, visitor_id, event_type, timestamp, zone_id=None, dwell_ms=0, is_staff=False, metadata=None):
        return {
            "event_id": str(uuid.uuid4()),
            "store_id": self.store_id,
            "camera_id": camera_id,
            "visitor_id": visitor_id,
            "event_type": event_type,
            "timestamp": timestamp.isoformat(),
            "zone_id": zone_id,
            "dwell_ms": dwell_ms,
            "is_staff": is_staff,
            "confidence": 0.95,
            "metadata": metadata or {}
        }
