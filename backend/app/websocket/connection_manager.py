import asyncio
import json
import logging
from typing import Dict, List
from fastapi import WebSocket
from app.websocket.redis_client import redis_client

logger = logging.getLogger("store_intelligence.websocket")

class ConnectionManager:
    def __init__(self):
        # Maps store_id to a list of active websocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.pubsub = redis_client.pubsub()
        self.listen_task = None

    async def connect(self, websocket: WebSocket, store_id: str):
        await websocket.accept()
        if store_id not in self.active_connections:
            self.active_connections[store_id] = []
            # Subscribe to the store's channel if this is the first connection
            await self.pubsub.subscribe(f"channel:metrics:{store_id}")
            logger.info(f"Subscribed to Redis channel: channel:metrics:{store_id}")
            
            # Start listener if not already running
            if self.listen_task is None or self.listen_task.done():
                self.listen_task = asyncio.create_task(self._listen())
                
        self.active_connections[store_id].append(websocket)

    def disconnect(self, websocket: WebSocket, store_id: str):
        if store_id in self.active_connections:
            if websocket in self.active_connections[store_id]:
                self.active_connections[store_id].remove(websocket)
            
            # If no more connections for this store, unsubscribe
            if not self.active_connections[store_id]:
                del self.active_connections[store_id]
                asyncio.create_task(self.pubsub.unsubscribe(f"channel:metrics:{store_id}"))
                logger.info(f"Unsubscribed from Redis channel: channel:metrics:{store_id}")

    async def broadcast(self, store_id: str, message: str):
        if store_id in self.active_connections:
            for connection in self.active_connections[store_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"WebSocket send failed: {e}")
                    self.disconnect(connection, store_id)

    async def _listen(self):
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = message["data"]
                    # Extract store_id from channel name (e.g., channel:metrics:ST1008)
                    parts = channel.split(":")
                    if len(parts) == 3:
                        store_id = parts[2]
                        await self.broadcast(store_id, data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis listener error: {e}")

manager = ConnectionManager()
