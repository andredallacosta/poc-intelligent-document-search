import logging
from typing import Dict, List, Optional
from uuid import UUID

import numpy as np
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.document import DocumentChunk
from domain.exceptions.document_exceptions import DocumentProcessingError
from domain.repositories.vector_repository import SearchResult, VectorRepository
from domain.value_objects.embedding import Embedding
from infrastructure.database.models import (
    DocumentoChunkModel,
    DocumentoEmbeddingModel,
    DocumentoModel,
)

logger = logging.getLogger(__name__)


class PostgresVectorRepository(VectorRepository):
    """Implementação PostgreSQL com pgvector do repositório de vetores"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_chunk_embedding(
        self, chunk_id: UUID, embedding: Embedding, metadata: Dict = None
    ) -> bool:
        """Adiciona embedding de um chunk"""
        try:
            chunk_exists = await self._chunk_exists(chunk_id)
            if not chunk_exists:
                raise DocumentProcessingError(f"Chunk {chunk_id} não encontrado")

            await self._delete_chunk_embedding_internal(chunk_id)

            vector_data = self._embedding_to_vector(embedding)

            model = DocumentoEmbeddingModel(
                chunk_id=chunk_id,
                embedding=vector_data,
            )

            self._session.add(model)
            await self._session.flush()

            logger.debug(f"Embedding adicionado para chunk {chunk_id}")
            return True

        except IntegrityError as e:
            await self._session.rollback()
            logger.error(f"Erro ao adicionar embedding para chunk {chunk_id}: {e}")
            raise DocumentProcessingError(f"Erro ao adicionar embedding: {e}")
        except Exception as e:
            logger.error(
                f"Erro inesperado ao adicionar embedding para chunk {chunk_id}: {e}"
            )
            raise DocumentProcessingError(f"Erro ao processar embedding: {e}")

    async def search_similar_chunks(
        self,
        query_embedding: Embedding,
        n_results: int = 5,
        similarity_threshold: float = 0.0,
        metadata_filter: Dict = None,
    ) -> List[SearchResult]:
        """Busca chunks similares usando pgvector"""
        try:
            query_vector = self._embedding_to_vector(query_embedding)

            stmt = select(
                DocumentoEmbeddingModel.embedding,
                DocumentoChunkModel.id,
                DocumentoChunkModel.conteudo,
                DocumentoChunkModel.documento_id,
                DocumentoChunkModel.indice_chunk,
                DocumentoChunkModel.start_char,
                DocumentoChunkModel.end_char,
                DocumentoChunkModel.criado_em,
                DocumentoModel.titulo,
                DocumentoModel.meta_data,
                (
                    1 - DocumentoEmbeddingModel.embedding.cosine_distance(query_vector)
                ).label("similarity_score"),
            ).select_from(
                DocumentoEmbeddingModel.__table__.join(
                    DocumentoChunkModel.__table__,
                    DocumentoEmbeddingModel.chunk_id == DocumentoChunkModel.id,
                ).join(
                    DocumentoModel.__table__,
                    DocumentoChunkModel.documento_id == DocumentoModel.id,
                )
            )

            if similarity_threshold > 0:
                stmt = stmt.where(
                    (
                        1
                        - DocumentoEmbeddingModel.embedding.cosine_distance(
                            query_vector
                        )
                    )
                    >= similarity_threshold
                )

            if metadata_filter:
                for key, value in metadata_filter.items():
                    stmt = stmt.where(
                        func.json_extract_path_text(DocumentoModel.meta_data, key)
                        == value
                    )

            stmt = stmt.order_by(
                (
                    1 - DocumentoEmbeddingModel.embedding.cosine_distance(query_vector)
                ).desc()
            ).limit(n_results)

            result = await self._session.execute(stmt)
            rows = result.fetchall()

            search_results = []
            for row in rows:
                chunk = DocumentChunk(
                    id=row.id,
                    document_id=row.documento_id,
                    content=row.conteudo,
                    original_content=row.conteudo,
                    chunk_index=row.indice_chunk,
                    start_char=row.start_char,
                    end_char=row.end_char,
                    embedding=self._vector_to_embedding(row.embedding),
                    created_at=row.criado_em,
                )

                similarity_score = float(row.similarity_score)
                distance = 1.0 - similarity_score

                doc_metadata = {
                    "document_title": row.titulo,
                    "document_metadata": row.meta_data or {},
                }

                search_result = SearchResult(
                    chunk=chunk,
                    similarity_score=similarity_score,
                    distance=distance,
                    metadata=doc_metadata,
                )

                search_results.append(search_result)

            logger.debug(f"Encontrados {len(search_results)} chunks similares")
            return search_results

        except Exception as e:
            logger.error(f"Erro na busca de similaridade: {e}")
            raise DocumentProcessingError(f"Erro na busca vetorial: {e}")

    async def delete_chunk_embedding(self, chunk_id: UUID) -> bool:
        """Remove embedding de um chunk"""
        return await self._delete_chunk_embedding_internal(chunk_id)

    async def delete_document_embeddings(self, document_id: UUID) -> int:
        """Remove todos os embeddings de um documento"""
        try:
            chunk_stmt = select(DocumentoChunkModel.id).where(
                DocumentoChunkModel.documento_id == document_id
            )
            chunk_result = await self._session.execute(chunk_stmt)
            chunk_ids = [row.id for row in chunk_result.fetchall()]

            if not chunk_ids:
                return 0

            delete_stmt = delete(DocumentoEmbeddingModel).where(
                DocumentoEmbeddingModel.chunk_id.in_(chunk_ids)
            )
            result = await self._session.execute(delete_stmt)

            deleted_count = result.rowcount
            logger.debug(
                f"Removidos {deleted_count} embeddings do documento {document_id}"
            )
            return deleted_count

        except Exception as e:
            logger.error(f"Erro ao remover embeddings do documento {document_id}: {e}")
            return 0

    async def update_chunk_embedding(
        self, chunk_id: UUID, embedding: Embedding, metadata: Dict = None
    ) -> bool:
        """Atualiza embedding de um chunk"""
        await self._delete_chunk_embedding_internal(chunk_id)
        return await self.add_chunk_embedding(chunk_id, embedding, metadata)

    async def get_embedding_by_chunk_id(self, chunk_id: UUID) -> Optional[Embedding]:
        """Busca embedding por ID do chunk"""
        try:
            stmt = select(DocumentoEmbeddingModel.embedding).where(
                DocumentoEmbeddingModel.chunk_id == chunk_id
            )
            result = await self._session.execute(stmt)
            vector_data = result.scalar_one_or_none()

            if vector_data is None:
                return None

            return self._vector_to_embedding(vector_data)

        except Exception as e:
            logger.error(f"Erro ao buscar embedding do chunk {chunk_id}: {e}")
            return None

    async def count_embeddings(self) -> int:
        """Conta total de embeddings"""
        try:
            stmt = select(func.count(DocumentoEmbeddingModel.id))
            result = await self._session.execute(stmt)
            return result.scalar()
        except Exception as e:
            logger.error(f"Erro ao contar embeddings: {e}")
            return 0

    async def embedding_exists(self, chunk_id: UUID) -> bool:
        """Verifica se embedding existe para o chunk"""
        try:
            stmt = select(func.count(DocumentoEmbeddingModel.id)).where(
                DocumentoEmbeddingModel.chunk_id == chunk_id
            )
            result = await self._session.execute(stmt)
            count = result.scalar()
            return count > 0
        except Exception as e:
            logger.error(
                f"Erro ao verificar existência de embedding para chunk {chunk_id}: {e}"
            )
            return False

    async def _delete_chunk_embedding_internal(self, chunk_id: UUID) -> bool:
        """Remove embedding de um chunk (método interno)"""
        try:
            stmt = delete(DocumentoEmbeddingModel).where(
                DocumentoEmbeddingModel.chunk_id == chunk_id
            )
            result = await self._session.execute(stmt)
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Erro ao remover embedding do chunk {chunk_id}: {e}")
            return False

    async def _chunk_exists(self, chunk_id: UUID) -> bool:
        """Verifica se chunk existe"""
        try:
            stmt = select(func.count(DocumentoChunkModel.id)).where(
                DocumentoChunkModel.id == chunk_id
            )
            result = await self._session.execute(stmt)
            count = result.scalar()
            return count > 0
        except Exception as e:
            logger.error(f"Erro ao verificar existência do chunk {chunk_id}: {e}")
            return False

    def _embedding_to_vector(self, embedding: Embedding) -> List[float]:
        """Converte Embedding para formato pgvector"""
        if isinstance(embedding.vector, np.ndarray):
            return embedding.vector.tolist()
        elif isinstance(embedding.vector, list):
            return embedding.vector
        else:
            raise DocumentProcessingError(
                f"Formato de embedding não suportado: {type(embedding.vector)}"
            )

    def _vector_to_embedding(self, vector_data) -> Embedding:
        """Converte dados pgvector para Embedding"""
        try:
            if hasattr(vector_data, "__iter__"):
                vector_list = list(vector_data)
            else:
                vector_list = vector_data

            return Embedding.from_openai(vector_list)
        except Exception as e:
            logger.error(f"Erro ao converter vector para embedding: {e}")
            raise DocumentProcessingError(f"Erro na conversão de embedding: {e}")

    async def optimize_index(self) -> bool:
        """Otimiza índice IVFFlat para melhor performance"""
        try:
            await self._session.execute(text("ANALYZE documento_embedding"))

            logger.info("Índice pgvector otimizado")
            return True
        except Exception as e:
            logger.error(f"Erro ao otimizar índice: {e}")
            return False
