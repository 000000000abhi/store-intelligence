import requests
import logging

logger = logging.getLogger("store_intelligence.stream_producer")

class StreamProducer:
    def __init__(self, api_url):
        self.api_url = api_url
        self.batch = []
        self.batch_size = 10

    def push(self, event):
        self.batch.append(event)
        if len(self.batch) >= self.batch_size:
            self.flush()

    def flush(self):
        if not self.batch:
            return
        
        try:
            response = requests.post(
                f"{self.api_url}/events/ingest",
                json=self.batch,
                timeout=2
            )
            response.raise_for_status()
            logger.info(f"Successfully pushed batch of {len(self.batch)} events.")
        except Exception as e:
            logger.error(f"Failed to push events: {e}")
            # Real implementation would queue for retry
        finally:
            self.batch = []
