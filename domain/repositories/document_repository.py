from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from domain.entities.document import Document, DocumentChunk
from domain.value_objects.embedding import Embedding


class DocumentRepository(ABC):

    @abstractmethod
    async def save(self, document: Document) -> Document:
        pass

    @abstractmethod
    async def find_by_id(self, document_id: UUID) -> Optional[Document]:
        pass

    @abstractmethod
    async def find_by_source(self, source: str) -> Optional[Document]:
        pass

    @abstractmethod
    async def find_all(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Document]:
        pass

    @abstractmethod
    async def delete(self, document_id: UUID) -> bool:
        pass

    @abstractmethod
    async def exists(self, source: str) -> bool:
        pass

    @abstractmethod
    async def count(self) -> int:
        pass
    
    @abstractmethod
    async def find_by_content_hash(self, content_hash: str) -> Optional[Document]:
        """Busca documento por hash do conteúdo (para deduplicação)"""
        pass


class DocumentChunkRepository(ABC):

    @abstractmethod
    async def save_chunk(self, chunk: DocumentChunk) -> DocumentChunk:
        pass

    @abstractmethod
    async def find_chunk_by_id(self, chunk_id: UUID) -> Optional[DocumentChunk]:
        pass

    @abstractmethod
    async def find_chunks_by_document_id(
        self, document_id: UUID
    ) -> List[DocumentChunk]:
        pass

    @abstractmethod
    async def delete_chunks_by_document_id(self, document_id: UUID) -> int:
        pass

    @abstractmethod
    async def update_chunk_embedding(
        self, chunk_id: UUID, embedding: Embedding
    ) -> bool:
        pass
