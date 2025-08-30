import redis.asyncio as redis
from typing import Optional
from api.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self):
        try:
            self.redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        if self.redis:
            await self.redis.close()
            logger.info("Redis disconnected")
    
    async def get(self, key: str) -> Optional[dict]:
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        try:
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Error getting key {key}: {e}")
            return None
    
    async def set(self, key: str, value: dict, ttl_seconds: Optional[int] = None) -> bool:
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        try:
            data = json.dumps(value)
            if ttl_seconds:
                return await self.redis.setex(key, ttl_seconds, data)
            else:
                return await self.redis.set(key, data)
        except Exception as e:
            logger.error(f"Error setting key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        try:
            return await self.redis.delete(key) > 0
        except Exception as e:
            logger.error(f"Error deleting key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking existence of key {key}: {e}")
            return False

redis_client = RedisClient()
