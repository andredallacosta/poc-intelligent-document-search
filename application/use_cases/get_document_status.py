import logging
from uuid import UUID

from application.dto.document_dto import DocumentStatusDTO
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.repositories.document_processing_job_repository import (
    DocumentProcessingJobRepository,
)

logger = logging.getLogger(__name__)


class GetDocumentStatusUseCase:
    """Use case para obter status de processamento de documento"""

    def __init__(self, job_repository: DocumentProcessingJobRepository):
        self.job_repository = job_repository

    async def execute(self, document_id: UUID) -> DocumentStatusDTO:
        """
        Obtém status atual do processamento de documento

        Args:
            document_id: ID do documento

        Returns:
            DocumentStatusDTO: Status detalhado do processamento

        Raises:
            BusinessRuleViolationError: Se documento não encontrado
        """
        try:
            job = await self.job_repository.find_by_document_id(document_id)
            if not job:
                raise BusinessRuleViolationError(
                    f"Documento não encontrado: {document_id}"
                )

            logger.info(
                f"Status consultado para documento {document_id}: {job.status.value}"
            )

            return DocumentStatusDTO(
                document_id=document_id,
                job_id=job.id,
                status=job.status,
                progress=job.progress,
                current_step=job.current_step,
                chunks_processed=job.chunks_processed,
                total_chunks=job.total_chunks,
                processing_time=job.processing_time_seconds,
                s3_file_deleted=job.s3_file_deleted,
                duplicate_of=job.duplicate_of,
                error=job.error_message,
                estimated_time_remaining=job.estimated_time_remaining,
            )

        except BusinessRuleViolationError:
            raise
        except Exception as e:
            logger.error(f"Erro ao obter status do documento {document_id}: {e}")
            raise BusinessRuleViolationError(f"Falha ao obter status: {str(e)}")


class GetJobStatusUseCase:
    """Use case para obter status por job_id"""

    def __init__(self, job_repository: DocumentProcessingJobRepository):
        self.job_repository = job_repository

    async def execute(self, job_id: UUID) -> DocumentStatusDTO:
        """
        Obtém status atual do job de processamento

        Args:
            job_id: ID do job

        Returns:
            DocumentStatusDTO: Status detalhado do processamento

        Raises:
            BusinessRuleViolationError: Se job não encontrado
        """
        try:
            job = await self.job_repository.find_by_id(job_id)
            if not job:
                raise BusinessRuleViolationError(f"Job não encontrado: {job_id}")

            logger.info(f"Status consultado para job {job_id}: {job.status.value}")

            return DocumentStatusDTO(
                document_id=job.document_id,
                job_id=job.id,
                status=job.status,
                progress=job.progress,
                current_step=job.current_step,
                chunks_processed=job.chunks_processed,
                total_chunks=job.total_chunks,
                processing_time=job.processing_time_seconds,
                s3_file_deleted=job.s3_file_deleted,
                duplicate_of=job.duplicate_of,
                error=job.error_message,
                estimated_time_remaining=job.estimated_time_remaining,
            )

        except BusinessRuleViolationError:
            raise
        except Exception as e:
            logger.error(f"Erro ao obter status do job {job_id}: {e}")
            raise BusinessRuleViolationError(f"Falha ao obter status: {str(e)}")
