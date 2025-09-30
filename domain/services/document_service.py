from typing import List, Optional
from uuid import UUID, uuid4

from domain.entities.document import Document, DocumentChunk
from domain.exceptions.document_exceptions import (
    DocumentAlreadyExistsError,
    DocumentNotFoundError,
    InvalidDocumentError,
)
from domain.repositories.document_repository import (
    DocumentChunkRepository,
    DocumentRepository,
)
from domain.value_objects.document_metadata import DocumentMetadata


class DocumentService:

    def __init__(
        self,
        document_repository: DocumentRepository,
        document_chunk_repository: DocumentChunkRepository = None,
    ):
        self._document_repository = document_repository
        self._document_chunk_repository = document_chunk_repository

    async def create_document(
        self,
        title: str,
        content: str,
        file_path: str,
        metadata: DocumentMetadata,
        skip_duplicate_check: bool = False,
    ) -> Document:
        if not title.strip():
            raise InvalidDocumentError("Document title cannot be empty")

        if not content.strip():
            raise InvalidDocumentError("Document content cannot be empty")

        if not skip_duplicate_check:
            if await self._document_repository.exists(metadata.source):
                raise DocumentAlreadyExistsError(
                    f"Document with source '{metadata.source}' already exists"
                )

        document = Document(
            id=uuid4(),
            title=title.strip(),
            content=content,
            file_path=file_path,
            metadata=metadata,
            chunks=[],
        )

        return await self._document_repository.save(document)

    async def get_document_by_id(self, document_id: UUID) -> Document:
        document = await self._document_repository.find_by_id(document_id)
        if not document:
            raise DocumentNotFoundError(f"Document with ID '{document_id}' not found")
        return document

    async def get_document_by_source(self, source: str) -> Optional[Document]:
        return await self._document_repository.find_by_source(source)

    async def list_documents(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Document]:
        return await self._document_repository.find_all(limit=limit, offset=offset)

    async def delete_document(self, document_id: UUID) -> bool:
        if not await self._document_repository.find_by_id(document_id):
            raise DocumentNotFoundError(f"Document with ID '{document_id}' not found")

        return await self._document_repository.delete(document_id)

    async def add_chunks_to_document(
        self, document_id: UUID, chunks: List[DocumentChunk]
    ) -> Document:
        document = await self.get_document_by_id(document_id)

        if self._document_chunk_repository:
            for chunk in chunks:
                chunk.document_id = document_id
                await self._document_chunk_repository.save_chunk(chunk)
        else:
            for chunk in chunks:
                chunk.document_id = document_id
                document.add_chunk(chunk)
            
            document = await self._document_repository.save(document)

        return document

    async def get_document_chunks(self, document_id: UUID) -> List[DocumentChunk]:
        """Retorna todos os chunks de um documento"""
        if self._document_chunk_repository:
            return await self._document_chunk_repository.find_chunks_by_document_id(
                document_id
            )
        else:
            document = await self.get_document_by_id(document_id)
            return document.chunks

    def validate_document_content(self, content: str) -> bool:
        if not content or not content.strip():
            return False

        if len(content.strip()) < 10:
            return False

        return True

    def calculate_document_stats(self, document: Document) -> dict:
        return {
            "word_count": document.word_count,
            "chunk_count": document.chunk_count,
            "file_size_mb": document.metadata.size_mb,
            "average_chunk_size": len(document.content) // max(document.chunk_count, 1),
        }
