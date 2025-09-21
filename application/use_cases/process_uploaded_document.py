import logging
from uuid import uuid4

from application.dto.document_dto import (
    ProcessDocumentRequestDTO,
    ProcessDocumentResponseDTO,
)
from domain.entities.document_processing_job import DocumentProcessingJob
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.repositories.document_processing_job_repository import (
    DocumentProcessingJobRepository,
)
from domain.repositories.file_upload_repository import FileUploadRepository
from domain.value_objects.processing_status import ProcessingStatus
from infrastructure.queue.redis_queue import redis_queue_service

logger = logging.getLogger(__name__)


class ProcessUploadedDocumentUseCase:
    """Use case para processar documento após upload"""
    
    def __init__(
        self,
        file_upload_repository: FileUploadRepository,
        job_repository: DocumentProcessingJobRepository
    ):
        self.file_upload_repository = file_upload_repository
        self.job_repository = job_repository
    
    async def execute(self, request: ProcessDocumentRequestDTO) -> ProcessDocumentResponseDTO:
        """
        Inicia processamento de documento após upload
        
        Args:
            request: Dados da solicitação de processamento
            
        Returns:
            ProcessDocumentResponseDTO: Dados do job de processamento
            
        Raises:
            BusinessRuleViolationError: Se upload não encontrado ou inválido
        """
        try:
            # Buscar FileUpload
            file_upload = await self.file_upload_repository.find_by_id(request.upload_id)
            if not file_upload:
                raise BusinessRuleViolationError(f"Upload não encontrado: {request.upload_id}")
            
            # Validar estado do upload
            self._validate_upload_state(file_upload)
            
            # Verificar se já existe job para este upload
            existing_job = await self.job_repository.find_by_upload_id(request.upload_id)
            if existing_job:
                logger.info(f"Job já existe para upload {request.upload_id}: {existing_job.id}")
                return ProcessDocumentResponseDTO(
                    job_id=existing_job.id,
                    status=existing_job.status,
                    estimated_time=self._get_estimated_time(existing_job.status)
                )
            
            # Criar job de processamento
            job = DocumentProcessingJob.create(
                document_id=file_upload.document_id,
                upload_id=request.upload_id,
                initial_step="Preparando processamento..."
            )
            
            # Salvar job
            await self.job_repository.save(job)
            
            # Marcar upload como processado
            file_upload.mark_uploaded()
            await self.file_upload_repository.save(file_upload)
            
            logger.info(f"Job de processamento criado: {job.id} para upload {request.upload_id}")
            
            # 🚀 REDIS QUEUE: Enfileirar processamento assíncrono REAL
            try:
                redis_job_id = redis_queue_service.enqueue_document_processing(
                    file_upload_id=file_upload.id,
                    job_id=job.id,
                    priority='normal'
                )
                
                # Salvar ID do job Redis no metadata
                job.metadata['redis_job_id'] = redis_job_id
                await self.job_repository.save(job)
                
                logger.info(f"Documento enfileirado no Redis - Job: {redis_job_id}, ProcessingJob: {job.id}")
                
            except Exception as e:
                logger.error(f"Erro ao enfileirar no Redis: {e}")
                # Marcar job como falhou
                job.fail_with_error(f"Falha ao enfileirar: {str(e)}")
                await self.job_repository.save(job)
                raise BusinessRuleViolationError(f"Falha ao iniciar processamento: {str(e)}")
            
            return ProcessDocumentResponseDTO(
                job_id=job.id,
                status=job.status,
                estimated_time=self._get_estimated_time(job.status)
            )
            
        except BusinessRuleViolationError:
            raise
        except Exception as e:
            logger.error(f"Erro ao processar documento: {e}")
            raise BusinessRuleViolationError(f"Falha no processamento: {str(e)}")
    
    def _validate_upload_state(self, file_upload) -> None:
        """Valida se upload está pronto para processamento"""
        if not file_upload.s3_key:
            raise BusinessRuleViolationError("Upload não possui chave S3")
        
        if file_upload.is_expired:
            raise BusinessRuleViolationError("Upload expirou")
        
        # Verificar se arquivo existe no S3 seria ideal, mas pode ser custoso
        # Em produção, isso seria verificado no processamento assíncrono
    
    
    def _get_estimated_time(self, status: ProcessingStatus) -> str:
        """Retorna tempo estimado baseado no status"""
        time_estimates = {
            ProcessingStatus.UPLOADED: "2-5 minutos",
            ProcessingStatus.EXTRACTING: "1-3 minutos",
            ProcessingStatus.CHECKING_DUPLICATES: "30 segundos",
            ProcessingStatus.CHUNKING: "1-2 minutos",
            ProcessingStatus.EMBEDDING: "2-4 minutos",
            ProcessingStatus.COMPLETED: "Concluído",
            ProcessingStatus.FAILED: "Falha",
            ProcessingStatus.DUPLICATE: "Concluído (duplicata)",
        }
        
        return time_estimates.get(status, "Tempo indeterminado")
