import asyncio
import logging
from typing import Any, Callable

from domain.exceptions.token_exceptions import TokenLockError
from domain.value_objects.municipality_id import MunicipalityId
from infrastructure.external.redis_client import RedisClient

logger = logging.getLogger(__name__)


class TokenLockService:
    """Service for distributed locks using Redis"""

    def __init__(self, redis_client: RedisClient):
        self._redis = redis_client
        self._lock_timeout = 10
        self._retry_delay = 0.1
        self._max_retries = 3

    async def with_period_lock(
        self, municipality_id: MunicipalityId, func: Callable, *args, **kwargs
    ) -> Any:
        """Executes function with distributed lock for period operations"""
        lock_key = f"period_lock:{municipality_id.value}"

        for attempt in range(self._max_retries):
            try:
                acquired = await self._acquire_lock(lock_key)
                if acquired:
                    break

                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))
                else:
                    raise TokenLockError(
                        "Operation in progress for this municipality. Try again in a few seconds."
                    )
            except Exception as e:
                logger.error(f"Error acquiring lock {lock_key}: {e}")
                raise TokenLockError("Internal error in concurrency control")

        try:
            return await func(*args, **kwargs)

        finally:
            await self._release_lock(lock_key)

    async def _acquire_lock(self, lock_key: str) -> bool:
        """Acquires lock with automatic TTL"""
        try:
            result = await self._redis.redis.set(
                lock_key, "locked", nx=True, ex=self._lock_timeout
            )
            return result is True
        except Exception as e:
            logger.error(f"Error acquiring lock {lock_key}: {e}")
            return False

    async def _release_lock(self, lock_key: str) -> None:
        """Releases lock explicitly"""
        try:
            await self._redis.delete(lock_key)
        except Exception as e:
            logger.warning(f"Error releasing lock {lock_key}: {e}")
