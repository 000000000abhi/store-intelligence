import logging
from app.database.database import SessionLocal

logger = logging.getLogger("store_intelligence.pos_worker")

async def run_pos_correlation():
    logger.info("Running POS correlation worker...")
    db = SessionLocal()
    try:
        import os
        import csv
        from datetime import datetime, timedelta
        from app.models.models import Transaction, VisitorSession, Event
        
        import glob
        
        # Find any POS CSV file in the /data directory
        csv_files = glob.glob("/data/POS*.csv") + glob.glob("/data/pos*.csv")
        if not csv_files:
            logger.warning("POS data file not found in /data")
            return
            
        csv_path = csv_files[0]
            
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Schema: order_id,order_date,order_time,store_id,product_id,brand_name,total_amount
            for row in reader:
                txn_id = row['order_id'].strip()
                store_id = row['store_id'].strip()
                if store_id.startswith("store_"):
                    store_id = store_id.replace("store_", "ST")
                    
                date_str = row['order_date'].strip()
                time_str = row['order_time'].strip()
                # 10-04-2026 12:15:05
                try:
                    txn_time = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M:%S")
                except ValueError:
                    continue
                    
                basket_val = float(row['total_amount'].strip())
                
                # Check if txn already exists
                existing = db.query(Transaction).filter(Transaction.invoice_number == txn_id).first()
                if not existing:
                    # Auto-upsert store
                    from sqlalchemy import text
                    db.execute(text("INSERT INTO stores (store_id, name, city, timezone) VALUES (:s, :n, 'AutoCity', 'UTC') ON CONFLICT (store_id) DO NOTHING"), {"s": store_id, "n": f"Store {store_id}"})
                    db.flush()
                    
                    # Look for an unconverted session in the billing zone within 5 mins prior
                    five_mins_prior = txn_time - timedelta(minutes=5)
                    
                    session = db.query(VisitorSession).join(Event, VisitorSession.visitor_id == Event.visitor_id)\
                        .filter(
                            VisitorSession.store_id == store_id,
                            VisitorSession.converted == False,
                            Event.event_type == 'BILLING_QUEUE_JOIN',
                            Event.timestamp >= five_mins_prior,
                            Event.timestamp <= txn_time
                        ).order_by(Event.timestamp.desc()).first()
                        
                    session_id = session.session_id if session else None
                    
                    txn = Transaction(
                        invoice_number=txn_id,
                        order_id=txn_id,
                        store_id=store_id,
                        order_date=txn_time.date(),
                        order_time=txn_time.time(),
                        gmv=basket_val,
                        nmv=basket_val,
                        correlated_session_id=session_id
                    )
                    db.add(txn)
                    
                    if session:
                        session.converted = True
                        session.current_state = 'PURCHASED'
                        
            # 2. Detect Abandonments
            # Any session that reached BILLING_QUEUE, has exited >5 mins ago, and is not converted
            now = datetime.utcnow()
            cutoff = now - timedelta(minutes=5)
            abandoned_sessions = db.query(VisitorSession).filter(
                VisitorSession.converted == False,
                VisitorSession.exit_time != None,
                VisitorSession.exit_time < cutoff,
                VisitorSession.current_state == 'BILLING_QUEUE'
            ).all()
            
            for session in abandoned_sessions:
                session.current_state = 'ABANDONED'
                # Optionally emit a BILLING_QUEUE_ABANDON event to the event stream here
                # (For now, just updating the session state is sufficient for metrics)
                
        db.commit()
    except Exception as e:
        logger.error(f"POS correlation failed: {e}")
    finally:
        db.close()
