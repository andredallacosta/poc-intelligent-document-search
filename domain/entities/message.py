from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4


class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(Enum):
    TEXT = "text"
    SEARCH_RESULT = "search_result"
    ERROR = "error"


@dataclass
class DocumentReference:
    document_id: UUID
    chunk_id: UUID
    source: str
    page: Optional[int] = None
    similarity_score: Optional[float] = None
    excerpt: Optional[str] = None


@dataclass
class Message:
    id: UUID
    session_id: UUID
    role: MessageRole
    content: str
    message_type: MessageType = MessageType.TEXT
    document_references: List[DocumentReference] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    created_at: datetime = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = uuid4()
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    @property
    def has_references(self) -> bool:
        return len(self.document_references) > 0
    
    @property
    def reference_count(self) -> int:
        return len(self.document_references)
    
    def add_document_reference(self, reference: DocumentReference) -> None:
        self.document_references.append(reference)
    
    def get_references_by_source(self, source: str) -> List[DocumentReference]:
        return [ref for ref in self.document_references if ref.source == source]
