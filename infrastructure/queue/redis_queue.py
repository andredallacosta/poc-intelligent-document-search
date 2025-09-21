import logging
from typing import Optional
from uuid import UUID

from rq import Queue, Worker
from rq.job import Job
from redis import Redis

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class RedisQueueService:
    """Serviço para gerenciar filas Redis usando RQ"""
    
    def __init__(self):
        self.redis_conn = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )
        
        # Filas específicas por tipo de processamento
        self.document_queue = Queue(
            'document_processing', 
            connection=self.redis_conn,
            default_timeout='30m'  # 30 minutos timeout
        )
        
        self.cleanup_queue = Queue(
            'cleanup_tasks',
            connection=self.redis_conn,
            default_timeout='5m'
        )
    
    def enqueue_document_processing(
        self, 
        file_upload_id: UUID, 
        job_id: UUID,
        priority: str = 'normal'
    ) -> str:
        """
        Enfileira job de processamento de documento
        
        Args:
            file_upload_id: ID do upload
            job_id: ID do job de processamento
            priority: Prioridade (high, normal, low)
            
        Returns:
            str: ID do job Redis
        """
        try:
            # Importar aqui para evitar circular imports
            from infrastructure.queue.jobs import process_document_job
            
            job = self.document_queue.enqueue(
                process_document_job,
                str(file_upload_id),
                str(job_id),
                job_timeout='30m',
                retry=3,  # 3 tentativas
                meta={
                    'priority': priority,
                    'type': 'document_processing',
                    'file_upload_id': str(file_upload_id),
                    'processing_job_id': str(job_id)
                }
            )
            
            logger.info(f"Job enfileirado: {job.id} para documento {file_upload_id}")
            return job.id
            
        except Exception as e:
            logger.error(f"Erro ao enfileirar job: {e}")
            raise
    
    def enqueue_cleanup_task(self, task_type: str, **kwargs) -> str:
        """
        Enfileira tarefa de limpeza (S3, arquivos órfãos, etc.)
        
        Args:
            task_type: Tipo da tarefa (s3_cleanup, orphaned_files, etc.)
            **kwargs: Parâmetros específicos da tarefa
            
        Returns:
            str: ID do job Redis
        """
        try:
            from infrastructure.queue.jobs import cleanup_task_job
            
            job = self.cleanup_queue.enqueue(
                cleanup_task_job,
                task_type,
                kwargs,
                job_timeout='5m',
                retry=2
            )
            
            logger.info(f"Tarefa de limpeza enfileirada: {job.id} - {task_type}")
            return job.id
            
        except Exception as e:
            logger.error(f"Erro ao enfileirar tarefa de limpeza: {e}")
            raise
    
    def get_job_status(self, job_id: str) -> Optional[dict]:
        """
        Obtém status de um job Redis
        
        Args:
            job_id: ID do job Redis
            
        Returns:
            dict: Status do job ou None se não encontrado
        """
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            
            return {
                'id': job.id,
                'status': job.get_status(),
                'created_at': job.created_at,
                'started_at': job.started_at,
                'ended_at': job.ended_at,
                'result': job.result,
                'exc_info': job.exc_info,
                'meta': job.meta
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter status do job {job_id}: {e}")
            return None
    
    def get_queue_info(self, queue_name: str = 'document_processing') -> dict:
        """
        Obtém informações da fila
        
        Args:
            queue_name: Nome da fila
            
        Returns:
            dict: Informações da fila
        """
        try:
            if queue_name == 'document_processing':
                queue = self.document_queue
            elif queue_name == 'cleanup_tasks':
                queue = self.cleanup_queue
            else:
                raise ValueError(f"Fila desconhecida: {queue_name}")
            
            return {
                'name': queue.name,
                'length': len(queue),
                'failed_count': queue.failed_job_registry.count,
                'started_count': queue.started_job_registry.count,
                'finished_count': queue.finished_job_registry.count,
                'deferred_count': queue.deferred_job_registry.count
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter info da fila {queue_name}: {e}")
            return {}
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancela um job
        
        Args:
            job_id: ID do job Redis
            
        Returns:
            bool: True se cancelado com sucesso
        """
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            job.cancel()
            
            logger.info(f"Job cancelado: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao cancelar job {job_id}: {e}")
            return False
    
    def retry_failed_job(self, job_id: str) -> bool:
        """
        Reprocessa um job que falhou
        
        Args:
            job_id: ID do job Redis
            
        Returns:
            bool: True se reenfileirado com sucesso
        """
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            job.retry()
            
            logger.info(f"Job reenfileirado: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao reprocessar job {job_id}: {e}")
            return False


# Instância global do serviço
redis_queue_service = RedisQueueService()
