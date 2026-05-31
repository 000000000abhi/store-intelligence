import logging
from datetime import datetime, timezone
from app.database.database import SessionLocal

logger = logging.getLogger("store_intelligence.metrics_worker")


async def run_metrics_snapshot():
    logger.info("Running metrics snapshot worker...")
    db = SessionLocal()
    try:
        from app.models.models import Store, Event, VisitorSession, MetricsSnapshot
        from sqlalchemy import func

        stores = db.query(Store).all()
        now = datetime.now(timezone.utc)

        for store in stores:
            store_id = store.store_id

            # 1. Unique visitors (non-staff)
            unique_visitors = db.query(func.count(func.distinct(Event.visitor_id)))\
                .filter(Event.store_id == store_id, Event.is_staff == False).scalar() or 0

            # 2. Average dwell time across sessions with dwell data
            avg_dwell_row = db.query(func.avg(VisitorSession.total_dwell_ms))\
                .filter(
                    VisitorSession.store_id == store_id,
                    VisitorSession.total_dwell_ms > 0
                ).scalar()
            avg_dwell_ms = float(avg_dwell_row) if avg_dwell_row is not None else 0.0

            # 3. Conversion rate: sessions that converted / total non-staff sessions
            total_sessions = db.query(func.count(VisitorSession.session_id))\
                .filter(VisitorSession.store_id == store_id).scalar() or 0
            converted_sessions = db.query(func.count(VisitorSession.session_id))\
                .filter(VisitorSession.store_id == store_id, VisitorSession.converted == True).scalar() or 0
            conversion_rate = round(converted_sessions / total_sessions, 4) if total_sessions > 0 else 0.0
            conversion_rate = max(0.0, min(1.0, conversion_rate))

            # 4. Current queue depth: sessions currently in BILLING_QUEUE state
            queue_depth = float(
                db.query(func.count(VisitorSession.session_id))
                .filter(
                    VisitorSession.store_id == store_id,
                    VisitorSession.current_state == 'BILLING_QUEUE'
                ).scalar() or 0
            )

            # 5. Abandonment rate: abandoned sessions / (abandoned + purchased)
            abandoned = db.query(func.count(VisitorSession.session_id))\
                .filter(VisitorSession.store_id == store_id, VisitorSession.current_state == 'ABANDONED').scalar() or 0
            purchased = converted_sessions
            denom = abandoned + purchased
            abandonment_rate = round(abandoned / denom, 4) if denom > 0 else 0.0

            # Write snapshot
            snapshot = MetricsSnapshot(
                store_id=store_id,
                snapshot_time=now,
                unique_visitors=unique_visitors,
                conversion_rate=conversion_rate,
                avg_dwell_ms=avg_dwell_ms,
                queue_depth=queue_depth,
                abandonment_rate=abandonment_rate,
            )
            db.add(snapshot)
            logger.info(
                f"Snapshot for {store_id}: visitors={unique_visitors}, "
                f"conv={conversion_rate:.2%}, dwell={avg_dwell_ms:.0f}ms, "
                f"queue={queue_depth}, abandon={abandonment_rate:.2%}"
            )

        db.commit()
    except Exception as e:
        logger.error(f"Metrics snapshot failed: {e}")
        db.rollback()
    finally:
        db.close()
