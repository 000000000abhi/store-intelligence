import logging
from datetime import datetime, timedelta, timezone
from app.database.database import SessionLocal

logger = logging.getLogger("store_intelligence.cleanup_worker")


async def run_session_cleanup():
    logger.info("Running session cleanup worker...")
    db = SessionLocal()
    try:
        from app.models.models import VisitorSession
        from sqlalchemy import func

        now = datetime.now(timezone.utc)
        stale_cutoff = now - timedelta(hours=2)

        # Find sessions that:
        # - Have been open (no exit_time) for more than 2 hours
        # - Are not already in a terminal state
        active_states = ('ENTERED', 'ZONE_VISIT', 'BILLING_QUEUE')
        stale_sessions = db.query(VisitorSession).filter(
            VisitorSession.current_state.in_(active_states),
            VisitorSession.exit_time == None,  # noqa: E711
            VisitorSession.entry_time < stale_cutoff
        ).all()

        if stale_sessions:
            logger.info(f"Closing {len(stale_sessions)} stale sessions.")
            for session in stale_sessions:
                session.exit_time = now
                session.current_state = 'EXITED'

            db.commit()
        else:
            logger.info("No stale sessions found.")

    except Exception as e:
        logger.error(f"Session cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()
