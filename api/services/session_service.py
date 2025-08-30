from typing import Optional
from datetime import datetime, timedelta
import json
import logging

from api.core.redis import redis_client
from api.core.config import settings
from api.models.session import SessionData

logger = logging.getLogger(__name__)

class SessionService:
    def __init__(self):
        self.ttl_seconds = settings.session_ttl_hours * 3600
        self.max_messages = settings.max_messages_per_session
        self.max_requests_per_day = settings.max_requests_per_session_day
    
    def _get_session_key(self, session_id: str) -> str:
        return f"session:{session_id}"
    
    async def create_session(self, session_id: Optional[str] = None) -> SessionData:
        session = SessionData(session_id=session_id) if session_id else SessionData()
        
        session_key = self._get_session_key(session.session_id)
        session_data = session.model_dump(mode='json')
        
        result = await redis_client.set(
            session_key,
            session_data,
            ttl_seconds=self.ttl_seconds
        )
        
        logger.info(f"Created session {session.session_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        data = await redis_client.get(self._get_session_key(session_id))
        
        if not data:
            return None
        
        try:
            session = SessionData(**data)
            await self._update_last_activity(session_id)
            return session
        except Exception as e:
            logger.error(f"Error parsing session {session_id}: {e}")
            return None
    
    async def update_session(self, session: SessionData) -> bool:
        return await redis_client.set(
            self._get_session_key(session.session_id),
            session.model_dump(mode='json'),
            ttl_seconds=self.ttl_seconds
        )
    
    async def add_message(self, session_id: str, role: str, content: str, tokens_used: Optional[int] = None) -> bool:
        session = await self.get_session(session_id)
        if not session:
            return False
        
        session.add_message(role, content, tokens_used)
        
        if len(session.messages) > self.max_messages:
            session.messages = session.messages[-self.max_messages:]
        
        return await self.update_session(session)
    
    async def check_rate_limit(self, session_id: str) -> bool:
        session = await self.get_session(session_id)
        if not session:
            return True
        
        today = datetime.now().date()
        last_activity_date = session.last_activity.date()
        
        if last_activity_date < today:
            session.requests_today = 0
            await self.update_session(session)
        
        return session.requests_today < self.max_requests_per_day
    
    async def delete_session(self, session_id: str) -> bool:
        return await redis_client.delete(self._get_session_key(session_id))
    
    async def _update_last_activity(self, session_id: str):
        session_key = self._get_session_key(session_id)
        await redis_client.redis.expire(session_key, self.ttl_seconds)

session_service = SessionService()
