from typing import Dict, List, Optional

from domain.entities.message import DocumentReference
from domain.exceptions.chat_exceptions import SearchError
from domain.repositories.vector_repository import SearchResult, VectorRepository
from domain.services.threshold_service import ThresholdService
from domain.value_objects.embedding import Embedding


class SearchService:

    def __init__(self, vector_repository: VectorRepository, threshold_service: Optional[ThresholdService] = None):
        self._vector_repository = vector_repository
        self._threshold_service = threshold_service

    async def search_similar_content(
        self,
        query: str,
        query_embedding: Embedding,
        n_results: int = 5,
        similarity_threshold: Optional[float] = None,
        metadata_filter: Dict = None,
    ) -> List[SearchResult]:
        """Search with adaptive threshold system"""
        try:
            # Use adaptive threshold if not explicitly provided
            if similarity_threshold is None:
                if self._threshold_service is not None:
                    similarity_threshold = self._threshold_service.get_threshold_for_query(query)
                else:
                    similarity_threshold = 0.45  # Fallback if no threshold service
            
            results = await self._vector_repository.search_similar_chunks(
                query_embedding=query_embedding,
                n_results=n_results,
                similarity_threshold=similarity_threshold,
                metadata_filter=metadata_filter,
            )

            return self._filter_and_rank_results(results, similarity_threshold)

        except Exception as e:
            raise SearchError(f"Failed to search similar content: {str(e)}")

    async def search_by_document_type(
        self, query: str, query_embedding: Embedding, document_type: str, n_results: int = 5
    ) -> List[SearchResult]:
        metadata_filter = {"file_type": document_type}

        return await self.search_similar_content(
            query=query,
            query_embedding=query_embedding,
            n_results=n_results,
            metadata_filter=metadata_filter,
        )

    async def search_by_source(
        self, query: str, query_embedding: Embedding, source: str, n_results: int = 5
    ) -> List[SearchResult]:
        metadata_filter = {"source": source}

        return await self.search_similar_content(
            query=query,
            query_embedding=query_embedding,
            n_results=n_results,
            metadata_filter=metadata_filter,
        )

    def convert_results_to_references(
        self, results: List[SearchResult]
    ) -> List[DocumentReference]:
        references = []

        for result in results:
            chunk = result.chunk
            metadata = result.metadata or {}
            reference = DocumentReference(
                document_id=chunk.document_id,
                chunk_id=chunk.id,
                source=metadata.get("source", "unknown"),
                page=metadata.get("page"),
                similarity_score=result.similarity_score,
                excerpt=self._create_excerpt(chunk.content),
            )
            references.append(reference)

        return references

    def _filter_and_rank_results(
        self, results: List[SearchResult], threshold: float
    ) -> List[SearchResult]:
        filtered_results = [
            result for result in results if result.similarity_score >= threshold
        ]

        return sorted(filtered_results, key=lambda x: x.similarity_score, reverse=True)

    def _create_excerpt(self, content: str, max_length: int = 200) -> str:
        if len(content) <= max_length:
            return content

        return content[:max_length].rsplit(" ", 1)[0] + "..."

    def calculate_relevance_score(
        self,
        similarity_score: float,
        document_popularity: float = 1.0,
        recency_factor: float = 1.0,
    ) -> float:
        return similarity_score * document_popularity * recency_factor
