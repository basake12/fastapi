# app/redis_client.py
import redis.asyncio as redis
from contextlib import asynccontextmanager
from .config import settings
import logging

logger = logging.getLogger("redis")
logger.setLevel(logging.INFO)

_redis_client = None


@asynccontextmanager
async def get_redis_client():
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
                retry_on_timeout=True,
            )
            await _redis_client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    try:
        yield _redis_client
    finally:
        pass


async def get_redis():
    async with get_redis_client() as client:
        yield client


redis_client = None


async def init_redis():
    global redis_client
    async with get_redis_client() as client:
        redis_client = client


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
        logger.info("Redis connection closed")