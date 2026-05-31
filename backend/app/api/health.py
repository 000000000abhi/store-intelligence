from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta, timezone
from app.database.database import get_db
from app.models.models import Store, Event
from app.schemas.schemas import HealthResponse

router = APIRouter()

# Camera IDs in use across the store
STORE_CAMERAS = ["CAM_ENTRY_01", "CAM_FLOOR_01", "CAM_FLOOR_02", "CAM_BILL_01", "CAM_BACK_01"]
STALE_THRESHOLD_MINUTES = 10


@router.get("/health", response_model=HealthResponse)
def get_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception:
        database_status = "disconnected"

    try:
        stores = [s.store_id for s in db.query(Store).all()]
    except Exception:
        stores = []

    # --- Camera last-event timestamps ---
    last_event_timestamps: dict[str, str] = {}
    stale_feed_warnings: list[str] = []

    try:
        now_utc = datetime.now(timezone.utc)
        stale_cutoff = now_utc - timedelta(minutes=STALE_THRESHOLD_MINUTES)

        # Query the most recent event timestamp per camera_id
        rows = db.query(
            Event.camera_id,
            func.max(Event.timestamp).label("last_ts")
        ).group_by(Event.camera_id).all()

        cam_latest: dict[str, datetime] = {}
        for row in rows:
            if row.camera_id and row.last_ts:
                cam_latest[row.camera_id] = row.last_ts

        for cam in STORE_CAMERAS:
            ts = cam_latest.get(cam)
            if ts is not None:
                # Ensure timezone-aware for comparison
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                last_event_timestamps[cam] = ts.isoformat()
                if ts < stale_cutoff:
                    stale_feed_warnings.append(
                        f"{cam}: last event {int((now_utc - ts).total_seconds() // 60)}m ago"
                    )
            # If no events at all for camera, it doesn't appear in timestamps
            # (frontend handles missing key as Disconnected, which is correct)

    except Exception:
        pass  # Don't let health endpoint fail due to timestamp query errors

    return HealthResponse(
        status="ok" if database_status == "connected" else "degraded",
        database=database_status,
        stores=stores,
        stale_feed_warnings=stale_feed_warnings,
        last_event_timestamps=last_event_timestamps,
    )
