import json
from datetime import timedelta
from typing import Any, Dict, List, Optional

import redis.asyncio as redis


class RedisClient:

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str = None,
        decode_responses: bool = True,
        url: str = None,
    ):
        if url:
            # Use URL if provided
            self.redis = redis.from_url(url, decode_responses=decode_responses)
        else:
            # Use individual parameters
            self.redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=decode_responses,
            )

    async def ping(self) -> bool:
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False

    async def set_json(
        self, key: str, value: Any, expire: Optional[timedelta] = None
    ) -> bool:
        try:
            json_value = json.dumps(value, default=str)
            if expire:
                return await self.redis.setex(key, expire, json_value)
            else:
                return await self.redis.set(key, json_value)
        except Exception:
            return False

    async def get_json(self, key: str) -> Optional[Any]:
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None

    async def delete(self, key: str) -> bool:
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        try:
            return await self.redis.exists(key) > 0
        except Exception:
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        try:
            return await self.redis.expire(key, seconds)
        except Exception:
            return False

    async def ttl(self, key: str) -> int:
        try:
            return await self.redis.ttl(key)
        except Exception:
            return -1

    async def increment(self, key: str, amount: int = 1) -> int:
        try:
            return await self.redis.incrby(key, amount)
        except Exception:
            return 0

    async def list_push(self, key: str, value: Any) -> int:
        try:
            json_value = json.dumps(value, default=str)
            return await self.redis.lpush(key, json_value)
        except Exception:
            return 0

    async def list_get_range(
        self, key: str, start: int = 0, end: int = -1
    ) -> List[Any]:
        try:
            values = await self.redis.lrange(key, start, end)
            return [json.loads(value) for value in values]
        except Exception:
            return []

    async def list_length(self, key: str) -> int:
        try:
            return await self.redis.llen(key)
        except Exception:
            return 0

    async def hash_set(self, key: str, field: str, value: Any) -> bool:
        try:
            json_value = json.dumps(value, default=str)
            return await self.redis.hset(key, field, json_value)
        except Exception:
            return False

    async def hash_get(self, key: str, field: str) -> Optional[Any]:
        try:
            value = await self.redis.hget(key, field)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None

    async def hash_get_all(self, key: str) -> Dict[str, Any]:
        try:
            hash_data = await self.redis.hgetall(key)
            return {field: json.loads(value) for field, value in hash_data.items()}
        except Exception:
            return {}

    async def hash_delete(self, key: str, field: str) -> bool:
        try:
            result = await self.redis.hdel(key, field)
            return result > 0
        except Exception:
            return False

    async def keys_pattern(self, pattern: str) -> List[str]:
        try:
            return await self.redis.keys(pattern)
        except Exception:
            return []

    async def close(self):
        try:
            await self.redis.close()
        except Exception:
            pass
