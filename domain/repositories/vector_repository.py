from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from uuid import UUID

from domain.entities.document import DocumentChunk
from domain.value_objects.embedding import Embedding


class SearchResult:
    def __init__(
        self,
        chunk: DocumentChunk,
        similarity_score: float,
        distance: float,
        metadata: Dict = None,
    ):
        self.chunk = chunk
        self.similarity_score = similarity_score
        self.distance = distance
        self.metadata = metadata or {}


class VectorRepository(ABC):

    @abstractmethod
    async def add_chunk_embedding(
        self, chunk_id: UUID, embedding: Embedding, metadata: Dict = None
    ) -> bool:
        pass

    @abstractmethod
    async def search_similar_chunks(
        self,
        query_embedding: Embedding,
        n_results: int = 5,
        similarity_threshold: float = 0.0,
        metadata_filter: Dict = None,
    ) -> List[SearchResult]:
        pass

    @abstractmethod
    async def delete_chunk_embedding(self, chunk_id: UUID) -> bool:
        pass

    @abstractmethod
    async def delete_document_embeddings(self, document_id: UUID) -> int:
        pass

    @abstractmethod
    async def update_chunk_embedding(
        self, chunk_id: UUID, embedding: Embedding, metadata: Dict = None
    ) -> bool:
        pass

    @abstractmethod
    async def get_embedding_by_chunk_id(self, chunk_id: UUID) -> Optional[Embedding]:
        pass

    @abstractmethod
    async def count_embeddings(self) -> int:
        pass

    @abstractmethod
    async def embedding_exists(self, chunk_id: UUID) -> bool:
        pass
