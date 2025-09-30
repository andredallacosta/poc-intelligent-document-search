from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import UUID


@dataclass
class ChatRequestDTO:
    message: str
    session_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class DocumentReferenceDTO:
    document_id: UUID
    chunk_id: UUID
    source: str
    page: Optional[int] = None
    similarity_score: Optional[float] = None
    excerpt: Optional[str] = None


@dataclass
class ChatResponseDTO:
    response: str
    session_id: UUID
    sources: List[DocumentReferenceDTO]
    metadata: Dict[str, Any]
    processing_time: float
    token_usage: Optional[Dict[str, int]] = None


@dataclass
class SearchRequestDTO:
    query: str
    n_results: int = 5
    similarity_threshold: Optional[float] = None
    document_type: Optional[str] = None
    source: Optional[str] = None


@dataclass
class SearchResultDTO:
    content: str
    source: str
    similarity_score: float
    metadata: Dict[str, Any]
    chunk_id: UUID
    document_id: UUID
