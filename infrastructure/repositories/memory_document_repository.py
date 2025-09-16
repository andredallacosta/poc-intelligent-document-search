from typing import Dict, List, Optional
from uuid import UUID

from domain.entities.document import Document, DocumentChunk
from domain.repositories.document_repository import DocumentRepository, DocumentChunkRepository
from domain.value_objects.embedding import Embedding


class MemoryDocumentRepository(DocumentRepository):
    """
    🚨 IMPLEMENTAÇÃO TEMPORÁRIA - REMOVER APÓS MIGRAÇÃO! 🚨
    
    Este arquivo existe apenas porque o DocumentRepository não tinha implementação concreta,
    causando quebra no DocumentService. É uma solução temporária para manter o sistema
    funcionando durante o desenvolvimento dos repositórios PostgreSQL.
    
    ❌ DELETAR TODO ESTE ARQUIVO quando implementar:
    - PostgresDocumentRepository
    - PostgresDocumentChunkRepository
    
    ✅ Substituto: infrastructure/repositories/postgres_document_repository.py
    
    Motivo: Clean Architecture exige implementações concretas das interfaces Domain.
    Sem isso, DocumentService não consegue ser instanciado no Container DI.
    """
    
    def __init__(self):
        self._documents: Dict[UUID, Document] = {}
        self._by_source: Dict[str, UUID] = {}
    
    async def save(self, document: Document) -> Document:
        self._documents[document.id] = document
        self._by_source[document.metadata.source] = document.id
        return document
    
    async def find_by_id(self, document_id: UUID) -> Optional[Document]:
        return self._documents.get(document_id)
    
    async def find_by_source(self, source: str) -> Optional[Document]:
        document_id = self._by_source.get(source)
        if document_id:
            return self._documents.get(document_id)
        return None
    
    async def find_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Document]:
        documents = list(self._documents.values())
        
        if offset > 0:
            documents = documents[offset:]
        
        if limit:
            documents = documents[:limit]
        
        return documents
    
    async def delete(self, document_id: UUID) -> bool:
        document = self._documents.get(document_id)
        if document:
            del self._documents[document_id]
            # Remove from source index
            source_to_remove = None
            for source, doc_id in self._by_source.items():
                if doc_id == document_id:
                    source_to_remove = source
                    break
            if source_to_remove:
                del self._by_source[source_to_remove]
            return True
        return False
    
    async def exists(self, source: str) -> bool:
        return source in self._by_source
    
    async def count(self) -> int:
        return len(self._documents)


class MemoryDocumentChunkRepository(DocumentChunkRepository):
    """
    🚨 IMPLEMENTAÇÃO TEMPORÁRIA - REMOVER APÓS MIGRAÇÃO! 🚨
    
    Complemento do MemoryDocumentRepository para chunks de documentos.
    Também será deletado quando implementarmos PostgreSQL.
    
    ❌ DELETAR junto com MemoryDocumentRepository
    ✅ Substituto: PostgresDocumentChunkRepository
    """
    
    def __init__(self):
        self._chunks: Dict[UUID, DocumentChunk] = {}
        self._by_document: Dict[UUID, List[UUID]] = {}
    
    async def save_chunk(self, chunk: DocumentChunk) -> DocumentChunk:
        self._chunks[chunk.id] = chunk
        
        # Update document index
        if chunk.document_id not in self._by_document:
            self._by_document[chunk.document_id] = []
        
        if chunk.id not in self._by_document[chunk.document_id]:
            self._by_document[chunk.document_id].append(chunk.id)
        
        return chunk
    
    async def find_chunk_by_id(self, chunk_id: UUID) -> Optional[DocumentChunk]:
        return self._chunks.get(chunk_id)
    
    async def find_chunks_by_document_id(self, document_id: UUID) -> List[DocumentChunk]:
        chunk_ids = self._by_document.get(document_id, [])
        chunks = []
        
        for chunk_id in chunk_ids:
            chunk = self._chunks.get(chunk_id)
            if chunk:
                chunks.append(chunk)
        
        # Sort by chunk_index
        chunks.sort(key=lambda c: c.chunk_index)
        return chunks
    
    async def delete_chunks_by_document_id(self, document_id: UUID) -> int:
        chunk_ids = self._by_document.get(document_id, [])
        deleted_count = 0
        
        for chunk_id in chunk_ids:
            if chunk_id in self._chunks:
                del self._chunks[chunk_id]
                deleted_count += 1
        
        if document_id in self._by_document:
            del self._by_document[document_id]
        
        return deleted_count
    
    async def update_chunk_embedding(self, chunk_id: UUID, embedding: Embedding) -> bool:
        chunk = self._chunks.get(chunk_id)
        if chunk:
            # In memory implementation doesn't store embeddings directly
            # This would be handled by the vector repository
            return True
        return False
