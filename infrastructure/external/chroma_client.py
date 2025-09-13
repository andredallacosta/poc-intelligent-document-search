import chromadb
from typing import Dict, List, Optional, Any
from uuid import UUID
import json

from domain.exceptions.document_exceptions import DocumentProcessingError
from infrastructure.config.settings import settings


class ChromaClient:
    
    def __init__(self, persist_directory: str = None, collection_name: str = None):
        self.persist_directory = persist_directory or settings.chroma_persist_directory
        self.collection_name = collection_name or settings.chroma_collection_name
        
        try:
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            raise DocumentProcessingError(f"Failed to initialize ChromaDB: {e}")
    
    async def add_embedding(
        self, 
        chunk_id: str, 
        embedding: List[float], 
        document: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        try:
            self.collection.add(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[document],
                metadatas=[metadata or {}]
            )
            return True
        except Exception as e:
            raise DocumentProcessingError(f"Failed to add embedding: {e}")
    
    async def add_embeddings_batch(
        self,
        chunk_ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]] = None
    ) -> bool:
        try:
            self.collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas or [{}] * len(chunk_ids)
            )
            return True
        except Exception as e:
            raise DocumentProcessingError(f"Failed to add batch embeddings: {e}")
    
    async def search_similar(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Dict[str, Any] = None,
        where_document: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=["documents", "metadatas", "distances"]
            )
            return results
        except Exception as e:
            raise DocumentProcessingError(f"Failed to search similar: {e}")
    
    async def delete_by_id(self, chunk_id: str) -> bool:
        try:
            self.collection.delete(ids=[chunk_id])
            return True
        except Exception as e:
            return False
    
    async def delete_by_filter(self, where: Dict[str, Any]) -> int:
        try:
            # Get IDs that match the filter first
            results = self.collection.get(where=where, include=[])
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                return len(results["ids"])
            return 0
        except Exception as e:
            return 0
    
    async def update_embedding(
        self,
        chunk_id: str,
        embedding: List[float] = None,
        document: str = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        try:
            update_data = {"ids": [chunk_id]}
            
            if embedding is not None:
                update_data["embeddings"] = [embedding]
            if document is not None:
                update_data["documents"] = [document]
            if metadata is not None:
                update_data["metadatas"] = [metadata]
            
            self.collection.update(**update_data)
            return True
        except Exception as e:
            return False
    
    async def get_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        try:
            results = self.collection.get(
                ids=[chunk_id],
                include=["documents", "metadatas", "embeddings"]
            )
            
            if results["ids"]:
                return {
                    "id": results["ids"][0],
                    "document": results["documents"][0] if results["documents"] else None,
                    "metadata": results["metadatas"][0] if results["metadatas"] else {},
                    "embedding": results["embeddings"][0] if results["embeddings"] else None
                }
            return None
        except Exception:
            return None
    
    async def count(self) -> int:
        try:
            return self.collection.count()
        except Exception:
            return 0
    
    async def exists(self, chunk_id: str) -> bool:
        try:
            results = self.collection.get(ids=[chunk_id], include=[])
            return len(results["ids"]) > 0
        except Exception:
            return False
    
    def reset_collection(self) -> bool:
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            return True
        except Exception:
            return False
