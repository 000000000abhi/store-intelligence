import time
import json
import logging
from uuid import uuid4
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("store_intelligence")
logger.setLevel(logging.INFO)
# Avoid double logging
if not logger.handlers:
    handler = logging.StreamHandler()
    logger.addHandler(handler)

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = str(uuid4())
        start_time = time.time()
        
        # Try to extract store_id from path if present
        store_id = None
        path_parts = request.url.path.split("/")
        if "stores" in path_parts:
            try:
                idx = path_parts.index("stores")
                if idx + 1 < len(path_parts):
                    store_id = path_parts[idx + 1]
            except Exception:
                pass
                
        # Default status for unhandled exceptions
        status_code = 500
        event_count = None
        
        try:
            # If it's ingest, we might want to peek at the body to count events,
            # but reading body in middleware can consume the stream.
            # We'll skip event_count in middleware for now and let the endpoint log it
            # or rely on custom logging there. But the requirement says: "Every request must contain... event_count (for ingest)"
            # A common pattern is to let the endpoint set it in request.state
            
            response = await call_next(request)
            status_code = response.status_code
            
            if hasattr(request.state, "event_count"):
                event_count = request.state.event_count
                
            return response
        finally:
            latency_ms = int((time.time() - start_time) * 1000)
            
            log_dict = {
                "trace_id": trace_id,
                "store_id": store_id,
                "endpoint": request.url.path,
                "method": request.method,
                "latency_ms": latency_ms,
                "status_code": status_code
            }
            if event_count is not None:
                log_dict["event_count"] = event_count
                
            logger.info(json.dumps(log_dict))
