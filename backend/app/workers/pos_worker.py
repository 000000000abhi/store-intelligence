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
        
        csv_path = "/data/pos_transactions.csv"
        if not os.path.exists(csv_path):
            logger.warning(f"POS data file not found at {csv_path}")
            return
            
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            # Schema: store_id, transaction_id, timestamp, basket_value_inr
            for row in reader:
                txn_id = row['transaction_id'].strip()
                store_id = row['store_id'].strip()
                txn_time = datetime.fromisoformat(row['timestamp'].strip().replace('Z', '+00:00'))
                basket_val = float(row['basket_value_inr'].strip())
                
                # Check if txn already exists
                existing = db.query(Transaction).filter(Transaction.invoice_number == txn_id).first()
                if not existing:
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
