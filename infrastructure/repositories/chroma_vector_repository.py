from typing import Dict, List, Optional
from uuid import UUID

from domain.entities.document import DocumentChunk
from domain.repositories.vector_repository import VectorRepository, SearchResult
from domain.value_objects.embedding import Embedding
from domain.exceptions.document_exceptions import DocumentProcessingError
from infrastructure.external.chroma_client import ChromaClient


class ChromaVectorRepository(VectorRepository):
    
    def __init__(self, chroma_client: ChromaClient):
        self._chroma_client = chroma_client
    
    async def add_chunk_embedding(
        self, 
        chunk_id: UUID, 
        embedding: Embedding, 
        metadata: Dict = None
    ) -> bool:
        try:
            chunk_metadata = metadata or {}
            chunk_metadata["chunk_id"] = str(chunk_id)
            
            return await self._chroma_client.add_embedding(
                chunk_id=str(chunk_id),
                embedding=embedding.vector,
                document="",  # Will be populated when we have the chunk content
                metadata=chunk_metadata
            )
        except Exception as e:
            raise DocumentProcessingError(f"Failed to add chunk embedding: {e}")
    
    async def search_similar_chunks(
        self, 
        query_embedding: Embedding, 
        n_results: int = 5,
        similarity_threshold: float = 0.0,
        metadata_filter: Dict = None
    ) -> List[SearchResult]:
        try:
            results = await self._chroma_client.search_similar(
                query_embedding=query_embedding.vector,
                n_results=n_results,
                where=metadata_filter
            )
            
            search_results = []
            
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    chunk_id = results["ids"][0][i]
                    distance = results["distances"][0][i]
                    similarity_score = 1 - distance  # Convert distance to similarity
                    
                    if similarity_score >= similarity_threshold:
                        metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                        document_text = results["documents"][0][i] if results["documents"] else ""
                        
                        # Create a minimal DocumentChunk for the search result
                        chunk = DocumentChunk(
                            id=UUID(chunk_id),
                            document_id=UUID(metadata.get("document_id", "00000000-0000-0000-0000-000000000000")),
                            content=document_text,
                            original_content=document_text,
                            chunk_index=metadata.get("chunk_index", 0),
                            start_char=metadata.get("start_char", 0),
                            end_char=metadata.get("end_char", 0)
                        )
                        
                        search_result = SearchResult(
                            chunk=chunk,
                            similarity_score=similarity_score,
                            distance=distance,
                            metadata=metadata
                        )
                        
                        search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            raise DocumentProcessingError(f"Failed to search similar chunks: {e}")
    
    async def delete_chunk_embedding(self, chunk_id: UUID) -> bool:
        try:
            return await self._chroma_client.delete_by_id(str(chunk_id))
        except Exception:
            return False
    
    async def delete_document_embeddings(self, document_id: UUID) -> int:
        try:
            return await self._chroma_client.delete_by_filter(
                where={"document_id": str(document_id)}
            )
        except Exception:
            return 0
    
    async def update_chunk_embedding(
        self, 
        chunk_id: UUID, 
        embedding: Embedding,
        metadata: Dict = None
    ) -> bool:
        try:
            chunk_metadata = metadata or {}
            chunk_metadata["chunk_id"] = str(chunk_id)
            
            return await self._chroma_client.update_embedding(
                chunk_id=str(chunk_id),
                embedding=embedding.vector,
                metadata=chunk_metadata
            )
        except Exception:
            return False
    
    async def get_embedding_by_chunk_id(self, chunk_id: UUID) -> Optional[Embedding]:
        try:
            result = await self._chroma_client.get_by_id(str(chunk_id))
            if result and result.get("embedding"):
                return Embedding.from_openai(result["embedding"])
            return None
        except Exception:
            return None
    
    async def count_embeddings(self) -> int:
        try:
            return await self._chroma_client.count()
        except Exception:
            return 0
    
    async def embedding_exists(self, chunk_id: UUID) -> bool:
        try:
            return await self._chroma_client.exists(str(chunk_id))
        except Exception:
            return False
