from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
from app.workers import pos_worker, anomaly_worker, metrics_worker, cleanup_worker

logger = logging.getLogger("store_intelligence.scheduler")
scheduler = AsyncIOScheduler()

def start_scheduler():
    # POS Correlation - every 60 seconds
    scheduler.add_job(pos_worker.run_pos_correlation, 'interval', seconds=60, id='pos_correlation')
    
    # Anomaly Evaluation - every 2 minutes
    scheduler.add_job(anomaly_worker.run_anomaly_evaluation, 'interval', minutes=2, id='anomaly_eval')
    
    # Metrics Snapshot - every 5 minutes
    scheduler.add_job(metrics_worker.run_metrics_snapshot, 'interval', minutes=5, id='metrics_snapshot')
    
    # Session Cleanup - every 15 minutes
    scheduler.add_job(cleanup_worker.run_session_cleanup, 'interval', minutes=15, id='session_cleanup')
    
    scheduler.start()
    logger.info("Scheduler started with all background workers.")

def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped.")
