import logging
from app.database.database import SessionLocal

logger = logging.getLogger("store_intelligence.anomaly_worker")

async def run_anomaly_evaluation():
    logger.info("Running anomaly evaluation worker...")
    db = SessionLocal()
    try:
        from app.models.models import Store, Event, Anomaly
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        now = datetime.utcnow()
        five_mins_ago = now - timedelta(minutes=5)
        thirty_mins_ago = now - timedelta(minutes=30)
        
        stores = db.query(Store).all()
        for store in stores:
            store_id = store.store_id
            
            # 1. Queue Spike: More than 5 people entered the queue in the last 5 mins
            queue_joins = db.query(func.count(func.distinct(Event.visitor_id)))\
                .filter(Event.store_id == store_id, Event.event_type == 'BILLING_QUEUE_JOIN', Event.timestamp >= five_mins_ago).scalar() or 0
                
            if queue_joins > 5:
                anomaly = Anomaly(
                    store_id=store_id,
                    type="BILLING_QUEUE_SPIKE",
                    severity="WARN",
                    description=f"Queue spike detected: {queue_joins} visitors joined the queue in the last 5 minutes.",
                    suggested_action="Open an additional checkout counter."
                )
                db.add(anomaly)
                
            # 2. Dead Zone: Zero entry events in the last 30 mins
            entries = db.query(func.count(func.distinct(Event.visitor_id)))\
                .filter(Event.store_id == store_id, Event.event_type == 'ENTRY', Event.timestamp >= thirty_mins_ago).scalar() or 0
                
            if entries == 0:
                anomaly = Anomaly(
                    store_id=store_id,
                    type="DEAD_ZONE",
                    severity="INFO",
                    description="No customers have entered the store in the last 30 minutes.",
                    suggested_action="Verify camera feed is online and store is open."
                )
                db.add(anomaly)
                
        db.commit()
    except Exception as e:
        logger.error(f"Anomaly evaluation failed: {e}")
    finally:
        db.close()
