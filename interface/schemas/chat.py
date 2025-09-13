from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    session_id: Optional[UUID] = Field(None, description="Session ID for conversation continuity")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Como escrever um ofício oficial?",
                "session_id": None,
                "metadata": {}
            }
        }


class DocumentSource(BaseModel):
    document_id: UUID = Field(..., description="Document ID")
    chunk_id: UUID = Field(..., description="Chunk ID")
    source: str = Field(..., description="Source file name")
    page: Optional[int] = Field(None, description="Page number")
    similarity_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Similarity score")
    excerpt: Optional[str] = Field(None, description="Text excerpt")


class ChatResponse(BaseModel):
    response: str = Field(..., description="AI generated response")
    session_id: UUID = Field(..., description="Session ID")
    sources: List[DocumentSource] = Field(default_factory=list, description="Document sources used")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")
    processing_time: float = Field(..., ge=0.0, description="Processing time in seconds")
    token_usage: Optional[Dict[str, int]] = Field(None, description="Token usage statistics")
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Para escrever um ofício oficial, você deve seguir a estrutura padrão...",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "sources": [
                    {
                        "document_id": "123e4567-e89b-12d3-a456-426614174001",
                        "chunk_id": "123e4567-e89b-12d3-a456-426614174002",
                        "source": "manual_redacao.pdf",
                        "page": 15,
                        "similarity_score": 0.89,
                        "excerpt": "O ofício é uma comunicação oficial..."
                    }
                ],
                "metadata": {
                    "message_id": "123e4567-e89b-12d3-a456-426614174003",
                    "search_results_count": 3,
                    "conversation_length": 2
                },
                "processing_time": 2.34,
                "token_usage": {
                    "prompt_tokens": 150,
                    "completion_tokens": 75,
                    "total_tokens": 225
                }
            }
        }


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    error_code: Optional[str] = Field(None, description="Error code")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Rate limit exceeded",
                "detail": "Maximum requests per day reached",
                "error_code": "RATE_LIMIT_EXCEEDED"
            }
        }
