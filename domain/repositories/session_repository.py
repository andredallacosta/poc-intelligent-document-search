from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from domain.entities.chat_session import ChatSession
from domain.entities.message import Message


class SessionRepository(ABC):
    
    @abstractmethod
    async def save_session(self, session: ChatSession) -> ChatSession:
        pass
    
    @abstractmethod
    async def find_session_by_id(self, session_id: UUID) -> Optional[ChatSession]:
        pass
    
    @abstractmethod
    async def find_active_sessions(self, limit: Optional[int] = None) -> List[ChatSession]:
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: UUID) -> bool:
        pass
    
    @abstractmethod
    async def deactivate_session(self, session_id: UUID) -> bool:
        pass
    
    @abstractmethod
    async def session_exists(self, session_id: UUID) -> bool:
        pass


class MessageRepository(ABC):
    
    @abstractmethod
    async def save_message(self, message: Message) -> Message:
        pass
    
    @abstractmethod
    async def find_message_by_id(self, message_id: UUID) -> Optional[Message]:
        pass
    
    @abstractmethod
    async def find_messages_by_session_id(
        self, 
        session_id: UUID, 
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        pass
    
    @abstractmethod
    async def delete_messages_by_session_id(self, session_id: UUID) -> int:
        pass
    
    @abstractmethod
    async def count_messages_by_session_id(self, session_id: UUID) -> int:
        pass
