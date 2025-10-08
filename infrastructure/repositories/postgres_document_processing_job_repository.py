import logging
from datetime import timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.document_processing_job import DocumentProcessingJob
from domain.repositories.document_processing_job_repository import (
    DocumentProcessingJobRepository,
)
from domain.value_objects.content_hash import ContentHash
from domain.value_objects.processing_status import ProcessingStatus
from infrastructure.database.models import DocumentProcessingJobModel

logger = logging.getLogger(__name__)


class PostgresDocumentProcessingJobRepository(DocumentProcessingJobRepository):
    """Implementação PostgreSQL do repositório de DocumentProcessingJob"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, job: DocumentProcessingJob) -> None:
        """Salva um DocumentProcessingJob"""
        try:
            stmt = select(DocumentProcessingJobModel).where(
                DocumentProcessingJobModel.id == job.id
            )
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.status = job.status.value
                existing.current_step = job.current_step
                existing.progress = job.progress
                existing.chunks_processed = job.chunks_processed
                existing.total_chunks = job.total_chunks
                existing.processing_time_seconds = job.processing_time_seconds
                existing.s3_file_deleted = job.s3_file_deleted
                existing.duplicate_of = job.duplicate_of
                existing.content_hash_algorithm = (
                    job.content_hash.algorithm if job.content_hash else None
                )
                existing.content_hash_value = (
                    job.content_hash.value if job.content_hash else None
                )
                existing.error_message = job.error_message
                existing.meta_data = job.metadata
                existing.started_at = job.started_at
                existing.completed_at = job.completed_at
            else:
                model = DocumentProcessingJobModel(
                    id=job.id,
                    document_id=job.document_id,
                    upload_id=job.upload_id,
                    status=job.status.value,
                    current_step=job.current_step,
                    progress=job.progress,
                    chunks_processed=job.chunks_processed,
                    total_chunks=job.total_chunks,
                    processing_time_seconds=job.processing_time_seconds,
                    s3_file_deleted=job.s3_file_deleted,
                    duplicate_of=job.duplicate_of,
                    content_hash_algorithm=(
                        job.content_hash.algorithm if job.content_hash else None
                    ),
                    content_hash_value=(
                        job.content_hash.value if job.content_hash else None
                    ),
                    error_message=job.error_message,
                    meta_data=job.metadata,
                    created_at=job.created_at,
                    started_at=job.started_at,
                    completed_at=job.completed_at,
                )
                self.session.add(model)

            await self.session.commit()
            logger.info(
                f"DocumentProcessingJob salvo: {job.id} - Status: {job.status.value}"
            )

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erro ao salvar DocumentProcessingJob {job.id}: {e}")
            raise

    async def find_by_id(self, job_id: UUID) -> Optional[DocumentProcessingJob]:
        """Busca job por ID"""
        try:
            stmt = select(DocumentProcessingJobModel).where(
                DocumentProcessingJobModel.id == job_id
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            if not model:
                return None

            return self._model_to_entity(model)

        except Exception as e:
            logger.error(f"Erro ao buscar DocumentProcessingJob {job_id}: {e}")
            return None

    async def find_by_document_id(
        self, document_id: UUID
    ) -> Optional[DocumentProcessingJob]:
        """Busca job por document_id"""
        try:
            stmt = select(DocumentProcessingJobModel).where(
                DocumentProcessingJobModel.document_id == document_id
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            if not model:
                return None

            return self._model_to_entity(model)

        except Exception as e:
            logger.error(
                f"Erro ao buscar DocumentProcessingJob por document_id {document_id}: {e}"
            )
            return None

    async def find_by_upload_id(
        self, upload_id: UUID
    ) -> Optional[DocumentProcessingJob]:
        """Busca job por upload_id"""
        try:
            stmt = select(DocumentProcessingJobModel).where(
                DocumentProcessingJobModel.upload_id == upload_id
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            if not model:
                return None

            return self._model_to_entity(model)

        except Exception as e:
            logger.error(
                f"Erro ao buscar DocumentProcessingJob por upload_id {upload_id}: {e}"
            )
            return None

    async def find_by_status(
        self, status: ProcessingStatus, limit: int = 100
    ) -> List[DocumentProcessingJob]:
        """Busca jobs por status"""
        try:
            stmt = (
                select(DocumentProcessingJobModel)
                .where(DocumentProcessingJobModel.status == status.value)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            models = result.scalars().all()

            return [self._model_to_entity(model) for model in models]

        except Exception as e:
            logger.error(
                f"Erro ao buscar DocumentProcessingJobs por status {status.value}: {e}"
            )
            return []

    async def find_processing_jobs(
        self, limit: int = 100
    ) -> List[DocumentProcessingJob]:
        """Busca jobs em processamento"""
        try:
            processing_statuses = [
                "extracting",
                "checking_duplicates",
                "chunking",
                "embedding",
            ]
            stmt = (
                select(DocumentProcessingJobModel)
                .where(DocumentProcessingJobModel.status.in_(processing_statuses))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            models = result.scalars().all()

            return [self._model_to_entity(model) for model in models]

        except Exception as e:
            logger.error(f"Erro ao buscar DocumentProcessingJobs em processamento: {e}")
            return []

    async def delete(self, job_id: UUID) -> bool:
        """Remove job"""
        try:
            stmt = delete(DocumentProcessingJobModel).where(
                DocumentProcessingJobModel.id == job_id
            )
            result = await self.session.execute(stmt)
            await self.session.commit()

            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"DocumentProcessingJob removido: {job_id}")

            return deleted

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erro ao remover DocumentProcessingJob {job_id}: {e}")
            return False

    def _model_to_entity(
        self, model: DocumentProcessingJobModel
    ) -> DocumentProcessingJob:
        """Converte model SQLAlchemy para entidade de domínio"""
        content_hash = None
        if model.content_hash_algorithm and model.content_hash_value:
            content_hash = ContentHash(
                algorithm=model.content_hash_algorithm, value=model.content_hash_value
            )

        # Ensure datetime fields are timezone-aware
        created_at = model.created_at
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        started_at = model.started_at
        if started_at and started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        completed_at = model.completed_at
        if completed_at and completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)

        job = DocumentProcessingJob(
            id=model.id,
            document_id=model.document_id,
            upload_id=model.upload_id,
            status=ProcessingStatus(model.status),
            current_step=model.current_step,
            progress=model.progress,
            chunks_processed=model.chunks_processed,
            total_chunks=model.total_chunks,
            processing_time_seconds=model.processing_time_seconds,
            s3_file_deleted=model.s3_file_deleted,
            duplicate_of=model.duplicate_of,
            content_hash=content_hash,
            error_message=model.error_message,
            metadata=model.meta_data or {},
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
        )

        return job
