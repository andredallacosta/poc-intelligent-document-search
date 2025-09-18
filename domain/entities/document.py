from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from domain.value_objects.document_metadata import DocumentMetadata
from domain.value_objects.embedding import Embedding


@dataclass
class DocumentChunk:
    id: UUID
    document_id: UUID
    content: str
    original_content: str
    chunk_index: int
    start_char: int
    end_char: int
    embedding: Optional[Embedding] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class Document:
    id: UUID
    title: str
    content: str
    file_path: str
    metadata: DocumentMetadata
    chunks: List[DocumentChunk]
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.id is None:
            self.id = uuid4()
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    @property
    def word_count(self) -> int:
        return len(self.content.split())

    def add_chunk(self, chunk: DocumentChunk) -> None:
        chunk.document_id = self.id
        self.chunks.append(chunk)
        self.updated_at = datetime.utcnow()

    def get_chunk_by_index(self, index: int) -> Optional[DocumentChunk]:
        for chunk in self.chunks:
            if chunk.chunk_index == index:
                return chunk
        return None
