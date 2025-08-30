from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChatRequest(BaseModel):
    message: str = Field(..., description="User message", min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, description="Session ID (auto-generated if not provided)")

class DocumentSource(BaseModel):
    source: str = Field(..., description="Document filename")
    page: Optional[int] = Field(None, description="Page number if applicable")
    chunk_index: Optional[int] = Field(None, description="Chunk index")
    similarity: float = Field(..., description="Similarity score")
    text_preview: str = Field(..., description="Preview of relevant text")

class ChatResponse(BaseModel):
    response: str = Field(..., description="AI assistant response")
    session_id: str = Field(..., description="Session ID for this conversation")
    sources: List[DocumentSource] = Field(default_factory=list, description="Source documents used")
    tokens_used: int = Field(..., description="Tokens consumed in this request")
    response_time_ms: int = Field(..., description="Response time in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.now)

class SessionHistoryResponse(BaseModel):
    session_id: str
    messages: List[Dict[str, Any]]
    total_messages: int
    created_at: datetime
    last_activity: datetime
    total_tokens_used: int

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    timestamp: datetime = Field(default_factory=datetime.now)
