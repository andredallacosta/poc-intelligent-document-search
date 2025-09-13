from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from domain.entities.message import Message


@dataclass
class ChatSession:
    id: UUID
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = None
    updated_at: datetime = None
    is_active: bool = True
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        if self.id is None:
            self.id = uuid4()
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    @property
    def message_count(self) -> int:
        return len(self.messages)
    
    @property
    def last_message(self) -> Optional[Message]:
        return self.messages[-1] if self.messages else None
    
    def add_message(self, message: Message) -> None:
        message.session_id = self.id
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
    
    def get_conversation_history(self, limit: Optional[int] = None) -> List[Message]:
        messages = sorted(self.messages, key=lambda m: m.created_at)
        if limit:
            return messages[-limit:]
        return messages
    
    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = datetime.utcnow()
