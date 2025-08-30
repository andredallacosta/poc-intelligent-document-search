from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class ChatMessage(BaseModel):
    role: str = Field(..., description="user or assistant")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now)
    tokens_used: Optional[int] = None

class SessionData(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    total_tokens_used: int = Field(default=0)
    requests_today: int = Field(default=0)
    
    def add_message(self, role: str, content: str, tokens_used: Optional[int] = None):
        message = ChatMessage(
            role=role, 
            content=content, 
            tokens_used=tokens_used
        )
        self.messages.append(message)
        self.last_activity = datetime.now()
        
        if tokens_used:
            self.total_tokens_used += tokens_used
        
        if role == "user":
            self.requests_today += 1
    
    def get_recent_messages(self, limit: int = 10) -> List[ChatMessage]:
        return self.messages[-limit:] if len(self.messages) > limit else self.messages
    
    def get_context_for_llm(self, max_tokens: int = 4000) -> List[dict]:
        messages = []
        current_tokens = 0
        
        for msg in reversed(self.messages):
            msg_tokens = len(msg.content.split()) * 1.3
            if current_tokens + msg_tokens > max_tokens:
                break
            
            messages.insert(0, {
                "role": msg.role,
                "content": msg.content
            })
            current_tokens += msg_tokens
        
        return messages
