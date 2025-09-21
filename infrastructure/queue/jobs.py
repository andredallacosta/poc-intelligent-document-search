import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from uuid import UUID

from rq import get_current_job

logger = logging.getLogger(__name__)


def process_document_job(file_upload_id: str, processing_job_id: str) -> Dict[str, Any]:
    """
    Job para processar documento de forma assíncrona
    
    Este job é executado pelo worker Redis em processo separado
    
    Args:
        file_upload_id: ID do FileUpload
        processing_job_id: ID do DocumentProcessingJob
        
    Returns:
        dict: Resultado do processamento
    """
    job = get_current_job()
    logger.info(f"Iniciando processamento de documento - Job: {job.id}")
    
    try:
        # Executar processamento assíncrono em loop de eventos
        result = asyncio.run(_process_document_async(file_upload_id, processing_job_id))
        
        logger.info(f"Documento processado com sucesso - Job: {job.id}")
        return {
            'status': 'completed',
            'document_id': result.get('document_id'),
            'processing_time': result.get('processing_time'),
            'chunks_created': result.get('chunks_created'),
            'embeddings_generated': result.get('embeddings_generated'),
            'completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro no processamento do documento - Job: {job.id}, Erro: {e}")
        
        # Atualizar job de processamento com erro
        asyncio.run(_update_job_with_error(processing_job_id, str(e)))
        
        # Re-raise para que RQ marque como failed
        raise


async def _process_document_async(file_upload_id: str, processing_job_id: str) -> Dict[str, Any]:
    """
    Processamento assíncrono real do documento
    
    Args:
        file_upload_id: ID do FileUpload
        processing_job_id: ID do DocumentProcessingJob
        
    Returns:
        dict: Resultado do processamento
    """
    from infrastructure.database.connection import get_async_session
    from infrastructure.repositories.postgres_file_upload_repository import PostgresFileUploadRepository
    from infrastructure.repositories.postgres_document_processing_job_repository import PostgresDocumentProcessingJobRepository
    from domain.services.document_processor import DocumentProcessor
    from infrastructure.repositories.postgres_document_repository import PostgresDocumentRepository
    from infrastructure.repositories.postgres_vector_repository import PostgresVectorRepository
    from infrastructure.external.s3_service import S3Service
    from infrastructure.external.openai_client import OpenAIClient
    from infrastructure.processors.text_chunker import TextChunker
    
    start_time = datetime.utcnow()
    
    # Criar sessão de banco de dados
    async with get_async_session() as session:
        # Repositórios
        file_upload_repo = PostgresFileUploadRepository(session)
        job_repo = PostgresDocumentProcessingJobRepository(session)
        document_repo = PostgresDocumentRepository(session)
        vector_repo = PostgresVectorRepository(session)
        
        # Serviços
        s3_service = S3Service()
        openai_client = OpenAIClient()
        text_chunker = TextChunker()
        
        # Document Processor
        document_processor = DocumentProcessor(
            document_repository=document_repo,
            vector_repository=vector_repo,
            s3_service=s3_service,
            openai_client=openai_client,
            text_chunker=text_chunker
        )
        
        # Buscar entidades
        file_upload = await file_upload_repo.find_by_id(UUID(file_upload_id))
        if not file_upload:
            raise ValueError(f"FileUpload não encontrado: {file_upload_id}")
        
        processing_job = await job_repo.find_by_id(UUID(processing_job_id))
        if not processing_job:
            raise ValueError(f"DocumentProcessingJob não encontrado: {processing_job_id}")
        
        # Processar documento
        document = await document_processor.process_uploaded_document(
            file_upload, processing_job
        )
        
        # Calcular tempo de processamento
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        # Atualizar tempo no job
        processing_job.processing_time_seconds = int(processing_time)
        await job_repo.save(processing_job)
        
        return {
            'document_id': str(document.id),
            'processing_time': processing_time,
            'chunks_created': processing_job.total_chunks,
            'embeddings_generated': processing_job.chunks_processed
        }


async def _update_job_with_error(processing_job_id: str, error_message: str) -> None:
    """
    Atualiza job de processamento com erro
    
    Args:
        processing_job_id: ID do DocumentProcessingJob
        error_message: Mensagem de erro
    """
    from infrastructure.database.connection import get_async_session
    from infrastructure.repositories.postgres_document_processing_job_repository import PostgresDocumentProcessingJobRepository
    
    async with get_async_session() as session:
        job_repo = PostgresDocumentProcessingJobRepository(session)
        
        processing_job = await job_repo.find_by_id(UUID(processing_job_id))
        if processing_job:
            processing_job.fail_with_error(error_message)
            await job_repo.save(processing_job)


def cleanup_task_job(task_type: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Job para tarefas de limpeza (S3, arquivos órfãos, etc.)
    
    Args:
        task_type: Tipo da tarefa
        kwargs: Parâmetros da tarefa
        
    Returns:
        dict: Resultado da limpeza
    """
    job = get_current_job()
    logger.info(f"Iniciando tarefa de limpeza: {task_type} - Job: {job.id}")
    
    try:
        if task_type == 's3_cleanup':
            result = asyncio.run(_cleanup_s3_files(**kwargs))
        elif task_type == 'orphaned_files':
            result = asyncio.run(_cleanup_orphaned_files(**kwargs))
        elif task_type == 'expired_uploads':
            result = asyncio.run(_cleanup_expired_uploads(**kwargs))
        else:
            raise ValueError(f"Tipo de tarefa desconhecido: {task_type}")
        
        logger.info(f"Tarefa de limpeza concluída: {task_type} - Job: {job.id}")
        return result
        
    except Exception as e:
        logger.error(f"Erro na tarefa de limpeza: {task_type} - Job: {job.id}, Erro: {e}")
        raise


async def _cleanup_s3_files(older_than_hours: int = 24) -> Dict[str, Any]:
    """
    Remove arquivos temporários antigos do S3
    
    Args:
        older_than_hours: Remover arquivos mais antigos que X horas
        
    Returns:
        dict: Resultado da limpeza
    """
    from infrastructure.external.s3_service import S3Service
    
    s3_service = S3Service()
    deleted_count = await s3_service.cleanup_temp_files(
        prefix="temp/",
        older_than_hours=older_than_hours
    )
    
    return {
        'task_type': 's3_cleanup',
        'deleted_count': deleted_count,
        'older_than_hours': older_than_hours,
        'completed_at': datetime.utcnow().isoformat()
    }


async def _cleanup_orphaned_files(**kwargs) -> Dict[str, Any]:
    """
    Remove registros de uploads órfãos (sem job de processamento)
    
    Returns:
        dict: Resultado da limpeza
    """
    from infrastructure.database.connection import get_async_session
    from infrastructure.repositories.postgres_file_upload_repository import PostgresFileUploadRepository
    from infrastructure.repositories.postgres_document_processing_job_repository import PostgresDocumentProcessingJobRepository
    from sqlalchemy import select, and_
    from infrastructure.database.models import FileUploadModel, DocumentProcessingJobModel
    from datetime import datetime, timedelta
    
    async with get_async_session() as session:
        # Buscar uploads sem jobs há mais de 1 hora
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        stmt = select(FileUploadModel).where(
            and_(
                FileUploadModel.created_at < cutoff_time,
                ~FileUploadModel.id.in_(
                    select(DocumentProcessingJobModel.upload_id)
                )
            )
        )
        
        result = await session.execute(stmt)
        orphaned_uploads = result.scalars().all()
        
        deleted_count = 0
        for upload in orphaned_uploads:
            await session.delete(upload)
            deleted_count += 1
        
        await session.commit()
        
        return {
            'task_type': 'orphaned_files',
            'deleted_count': deleted_count,
            'completed_at': datetime.utcnow().isoformat()
        }


async def _cleanup_expired_uploads(**kwargs) -> Dict[str, Any]:
    """
    Remove uploads expirados
    
    Returns:
        dict: Resultado da limpeza
    """
    from infrastructure.database.connection import get_async_session
    from infrastructure.repositories.postgres_file_upload_repository import PostgresFileUploadRepository
    from sqlalchemy import select, and_
    from infrastructure.database.models import FileUploadModel
    from datetime import datetime
    
    async with get_async_session() as session:
        # Buscar uploads expirados
        now = datetime.utcnow()
        
        stmt = select(FileUploadModel).where(
            and_(
                FileUploadModel.expires_at.is_not(None),
                FileUploadModel.expires_at < now
            )
        )
        
        result = await session.execute(stmt)
        expired_uploads = result.scalars().all()
        
        deleted_count = 0
        for upload in expired_uploads:
            await session.delete(upload)
            deleted_count += 1
        
        await session.commit()
        
        return {
            'task_type': 'expired_uploads',
            'deleted_count': deleted_count,
            'completed_at': datetime.utcnow().isoformat()
        }
