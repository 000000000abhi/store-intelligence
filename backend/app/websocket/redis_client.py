import os
import redis.asyncio as redis
import json
import logging

logger = logging.getLogger("store_intelligence.redis")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

async def publish_message(channel: str, message: dict):
    try:
        await redis_client.publish(channel, json.dumps(message))
    except Exception as e:
        logger.error(f"Failed to publish to redis channel {channel}: {e}")

async def get_redis_client():
    return redis_client
