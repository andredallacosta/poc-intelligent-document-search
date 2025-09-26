import hashlib
import logging
from typing import Dict, List, Optional

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.document import Document, DocumentChunk
from domain.exceptions.document_exceptions import DocumentProcessingError
from domain.repositories.document_repository import (
    DocumentChunkRepository,
    DocumentRepository,
)
from domain.value_objects.document_metadata import DocumentMetadata
from domain.value_objects.embedding import Embedding
from infrastructure.database.models import DocumentoChunkModel, DocumentoModel

logger = logging.getLogger(__name__)


class PostgresDocumentRepository(DocumentRepository):
    """Implementação PostgreSQL do repositório de Document"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, document: Document) -> Document:
        """Salva um documento"""
        try:
            file_hash = (
                self._calculate_file_hash(document.content)
                if document.content
                else None
            )

            existing_stmt = select(DocumentoModel).where(
                DocumentoModel.id == document.id
            )
            existing_result = await self._session.execute(existing_stmt)
            existing_model = existing_result.scalar_one_or_none()

            if existing_model:
                existing_model.titulo = document.title
                existing_model.conteudo = document.content
                existing_model.caminho_arquivo = document.metadata.source
                existing_model.file_hash = file_hash
                existing_model.meta_data = self._metadata_to_dict(document.metadata)
                existing_model.atualizado_em = document.updated_at

                await self._session.flush()
                return document
            else:
                model = DocumentoModel(
                    id=document.id,
                    titulo=document.title,
                    conteudo=document.content,
                    caminho_arquivo=document.metadata.source,
                    file_hash=file_hash,
                    meta_data=self._metadata_to_dict(document.metadata),
                    criado_em=document.created_at,
                    atualizado_em=document.updated_at,
                )

                self._session.add(model)
                await self._session.flush()
                return document

        except IntegrityError as e:
            await self._session.rollback()
            if "unique constraint" in str(e).lower():
                if "source" in str(e).lower():
                    raise DocumentProcessingError(
                        f"Documento com source '{document.metadata.source}' já existe"
                    )
                elif "file_hash" in str(e).lower():
                    raise DocumentProcessingError(
                        "Documento com conteúdo idêntico já existe"
                    )
            raise DocumentProcessingError(f"Erro ao salvar documento: {e}")

    async def find_by_id(self, document_id) -> Optional[Document]:
        """Busca documento por ID"""
        stmt = select(DocumentoModel).where(DocumentoModel.id == document_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_entity(model)

    async def find_by_source(self, source: str) -> Optional[Document]:
        """Busca documento por source"""
        stmt = select(DocumentoModel).where(
            func.json_extract_path_text(DocumentoModel.meta_data, "source") == source
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_entity(model)

    async def find_all(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Document]:
        """Lista todos os documentos"""
        stmt = select(DocumentoModel).order_by(DocumentoModel.criado_em.desc())

        if limit:
            stmt = stmt.limit(limit)
        if offset > 0:
            stmt = stmt.offset(offset)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def find_by_title_similarity(
        self, title: str, threshold: float = 0.8
    ) -> List[Document]:
        """Busca documentos por similaridade de título"""
        stmt = (
            select(DocumentoModel)
            .where(func.similarity(DocumentoModel.titulo, title) > threshold)
            .order_by(func.similarity(DocumentoModel.titulo, title).desc())
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def find_by_content_search(
        self, search_term: str, limit: int = 10
    ) -> List[Document]:
        """Busca documentos por termo no conteúdo"""
        stmt = (
            select(DocumentoModel)
            .where(
                or_(
                    DocumentoModel.titulo.ilike(f"%{search_term}%"),
                    DocumentoModel.conteudo.ilike(f"%{search_term}%"),
                )
            )
            .order_by(DocumentoModel.criado_em.desc())
            .limit(limit)
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def update(self, document: Document) -> Document:
        """Atualiza um documento"""
        try:
            file_hash = (
                self._calculate_file_hash(document.content)
                if document.content
                else None
            )

            stmt = (
                update(DocumentoModel)
                .where(DocumentoModel.id == document.id)
                .values(
                    titulo=document.title,
                    conteudo=document.content,
                    caminho_arquivo=document.metadata.source,
                    file_hash=file_hash,
                    meta_data=self._metadata_to_dict(document.metadata),
                    atualizado_em=document.updated_at,
                )
            )

            result = await self._session.execute(stmt)

            if result.rowcount == 0:
                raise DocumentProcessingError(f"Documento {document.id} não encontrado")

            return document

        except IntegrityError as e:
            await self._session.rollback()
            if "unique constraint" in str(e).lower():
                if "source" in str(e).lower():
                    raise DocumentProcessingError(
                        f"Documento com source '{document.metadata.source}' já existe"
                    )
                elif "file_hash" in str(e).lower():
                    raise DocumentProcessingError(
                        "Documento com conteúdo idêntico já existe"
                    )
            raise DocumentProcessingError(f"Erro ao atualizar documento: {e}")

    async def delete(self, document_id) -> bool:
        """Remove um documento"""
        stmt = delete(DocumentoModel).where(DocumentoModel.id == document_id)
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def exists(self, source: str) -> bool:
        """Verifica se existe documento com o source"""
        stmt = select(func.count(DocumentoModel.id)).where(
            func.json_extract_path_text(DocumentoModel.meta_data, "source") == source
        )
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count > 0

    async def exists_by_content_hash(self, content: str) -> bool:
        """Verifica se existe documento com conteúdo idêntico"""
        file_hash = self._calculate_file_hash(content)
        stmt = select(func.count(DocumentoModel.id)).where(
            DocumentoModel.file_hash == file_hash
        )
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count > 0

    async def count(self) -> int:
        """Conta total de documentos"""
        stmt = select(func.count(DocumentoModel.id))
        result = await self._session.execute(stmt)
        return result.scalar()

    async def find_by_content_hash(self, content_hash: str) -> Optional[Document]:
        """Busca documento por hash do conteúdo (para deduplicação)"""
        stmt = select(DocumentoModel).where(DocumentoModel.file_hash == content_hash)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_entity(model)

    def _calculate_file_hash(self, content: str) -> str:
        """Calcula hash SHA256 do conteúdo"""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _metadata_to_dict(self, metadata: DocumentMetadata) -> Dict:
        """Converte DocumentMetadata para dict"""
        return {
            "source": metadata.source,
            "document_type": metadata.file_type,
            "language": metadata.language,
            "author": metadata.author,
            "created_date": (
                metadata.creation_date.isoformat() if metadata.creation_date else None
            ),
            "modified_date": (
                metadata.modification_date.isoformat()
                if metadata.modification_date
                else None
            ),
            "file_size": metadata.file_size,
            "page_count": metadata.page_count,
            "word_count": metadata.word_count,
            "title": metadata.title,
            "subject": metadata.subject,
            "custom_fields": metadata.custom_fields,
        }

    def _dict_to_metadata(self, data: Dict) -> DocumentMetadata:
        """Converte dict para DocumentMetadata"""
        from datetime import datetime

        return DocumentMetadata(
            source=data.get("source", ""),
            file_type=data.get("document_type", "unknown"),
            file_size=data.get("file_size", 0),
            language=data.get("language"),
            author=data.get("author"),
            title=data.get("title"),
            subject=data.get("subject"),
            creation_date=(
                datetime.fromisoformat(data["created_date"])
                if data.get("created_date")
                else None
            ),
            modification_date=(
                datetime.fromisoformat(data["modified_date"])
                if data.get("modified_date")
                else None
            ),
            page_count=data.get("page_count"),
            word_count=data.get("word_count"),
            custom_fields=data.get("custom_fields", {}),
        )

    def _model_to_entity(self, model: DocumentoModel) -> Document:
        """Converte model para entidade"""
        metadata = self._dict_to_metadata(model.meta_data or {})

        return Document(
            id=model.id,
            title=model.titulo,
            content=model.conteudo,
            file_path=metadata.source,
            metadata=metadata,
            chunks=[],
            created_at=model.criado_em,
            updated_at=model.atualizado_em,
        )


class PostgresDocumentChunkRepository(DocumentChunkRepository):
    """Implementação PostgreSQL do repositório de DocumentChunk"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save_chunk(self, chunk: DocumentChunk) -> DocumentChunk:
        """Salva um chunk de documento"""
        try:
            model = DocumentoChunkModel(
                id=chunk.id,
                documento_id=chunk.document_id,
                conteudo=chunk.content,
                indice_chunk=chunk.chunk_index,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                meta_data={},
                criado_em=chunk.created_at,
            )

            self._session.add(model)
            await self._session.flush()

            return chunk

        except IntegrityError as e:
            await self._session.rollback()
            if "unique constraint" in str(e).lower():
                raise DocumentProcessingError(
                    f"Chunk {chunk.chunk_index} já existe para documento {chunk.document_id}"
                )
            raise DocumentProcessingError(f"Erro ao salvar chunk: {e}")

    async def find_chunk_by_id(self, chunk_id) -> Optional[DocumentChunk]:
        """Busca chunk por ID"""
        stmt = select(DocumentoChunkModel).where(DocumentoChunkModel.id == chunk_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_entity(model)

    async def find_chunks_by_document_id(self, document_id) -> List[DocumentChunk]:
        """Busca chunks de um documento"""
        stmt = (
            select(DocumentoChunkModel)
            .where(DocumentoChunkModel.documento_id == document_id)
            .order_by(DocumentoChunkModel.indice_chunk)
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def delete_chunks_by_document_id(self, document_id) -> int:
        """Remove chunks de um documento"""
        stmt = delete(DocumentoChunkModel).where(
            DocumentoChunkModel.documento_id == document_id
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def update_chunk_embedding(self, chunk_id, embedding: Embedding) -> bool:
        """Atualiza embedding de um chunk (implementado no VectorRepository)"""
        return True

    def _model_to_entity(self, model: DocumentoChunkModel) -> DocumentChunk:
        """Converte model para entidade"""
        return DocumentChunk(
            id=model.id,
            document_id=model.documento_id,
            content=model.conteudo,
            original_content=model.conteudo,
            chunk_index=model.indice_chunk,
            start_char=model.start_char,
            end_char=model.end_char,
            embedding=None,
            created_at=model.criado_em,
        )
