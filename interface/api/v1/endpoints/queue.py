import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from infrastructure.queue.redis_queue import redis_queue_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/queue", tags=["Queue Management"])


class QueueInfoResponse(BaseModel):
    """Response para informações da fila"""

    name: str = Field(..., description="Nome da fila")
    length: int = Field(..., description="Número de jobs na fila")
    failed_count: int = Field(..., description="Jobs que falharam")
    started_count: int = Field(..., description="Jobs em execução")
    finished_count: int = Field(..., description="Jobs concluídos")
    deferred_count: int = Field(..., description="Jobs adiados")


class JobStatusResponse(BaseModel):
    """Response para status de job Redis"""

    id: str = Field(..., description="ID do job Redis")
    status: str = Field(..., description="Status do job")
    created_at: str = Field(..., description="Data de criação")
    started_at: str = Field(None, description="Data de início")
    ended_at: str = Field(None, description="Data de fim")
    result: Dict[str, Any] = Field(None, description="Resultado do job")
    exc_info: str = Field(None, description="Informações de erro")
    meta: Dict[str, Any] = Field(..., description="Metadados do job")


class CleanupTaskRequest(BaseModel):
    """Request para tarefa de limpeza"""

    task_type: str = Field(
        ..., description="Tipo da tarefa (s3_cleanup, orphaned_files, expired_uploads)"
    )
    older_than_hours: int = Field(
        24, description="Para s3_cleanup: remover arquivos mais antigos que X horas"
    )


@router.get("/info", response_model=List[QueueInfoResponse])
async def get_queue_info():
    """
    Obtém informações sobre todas as filas Redis

    Returns:
        List[QueueInfoResponse]: Informações das filas
    """
    try:
        queues = ["document_processing", "cleanup_tasks"]
        queue_info = []

        for queue_name in queues:
            info = redis_queue_service.get_queue_info(queue_name)
            if info:
                queue_info.append(QueueInfoResponse(**info))

        return queue_info

    except Exception as e:
        logger.error(f"Erro ao obter informações das filas: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.get("/info/{queue_name}", response_model=QueueInfoResponse)
async def get_specific_queue_info(queue_name: str):
    """
    Obtém informações de uma fila específica

    Args:
        queue_name: Nome da fila (document_processing ou cleanup_tasks)

    Returns:
        QueueInfoResponse: Informações da fila
    """
    try:
        if queue_name not in ["document_processing", "cleanup_tasks"]:
            raise HTTPException(
                status_code=400,
                detail=f"Fila inválida: {queue_name}. Use: document_processing ou cleanup_tasks",
            )

        info = redis_queue_service.get_queue_info(queue_name)
        if not info:
            raise HTTPException(
                status_code=404, detail=f"Fila não encontrada: {queue_name}"
            )

        return QueueInfoResponse(**info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter informações da fila {queue_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Obtém status de um job Redis específico

    Args:
        job_id: ID do job Redis

    Returns:
        JobStatusResponse: Status do job
    """
    try:
        job_status = redis_queue_service.get_job_status(job_id)
        if not job_status:
            raise HTTPException(status_code=404, detail=f"Job não encontrado: {job_id}")

        return JobStatusResponse(
            id=job_status["id"],
            status=job_status["status"],
            created_at=(
                job_status["created_at"].isoformat()
                if job_status["created_at"]
                else None
            ),
            started_at=(
                job_status["started_at"].isoformat()
                if job_status["started_at"]
                else None
            ),
            ended_at=(
                job_status["ended_at"].isoformat() if job_status["ended_at"] else None
            ),
            result=job_status["result"] or {},
            exc_info=job_status["exc_info"],
            meta=job_status["meta"] or {},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter status do job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.post("/job/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancela um job Redis

    Args:
        job_id: ID do job Redis

    Returns:
        dict: Resultado da operação
    """
    try:
        success = redis_queue_service.cancel_job(job_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Job não encontrado ou não pode ser cancelado: {job_id}",
            )

        return {
            "message": f"Job {job_id} cancelado com sucesso",
            "job_id": job_id,
            "status": "cancelled",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao cancelar job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.post("/job/{job_id}/retry")
async def retry_job(job_id: str):
    """
    Reprocessa um job que falhou

    Args:
        job_id: ID do job Redis

    Returns:
        dict: Resultado da operação
    """
    try:
        success = redis_queue_service.retry_failed_job(job_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Job não encontrado ou não pode ser reprocessado: {job_id}",
            )

        return {
            "message": f"Job {job_id} reenfileirado com sucesso",
            "job_id": job_id,
            "status": "queued",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao reprocessar job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.post("/cleanup")
async def enqueue_cleanup_task(request: CleanupTaskRequest):
    """
    Enfileira tarefa de limpeza

    Args:
        request: Dados da tarefa de limpeza

    Returns:
        dict: ID do job criado
    """
    try:
        valid_tasks = ["s3_cleanup", "orphaned_files", "expired_uploads"]
        if request.task_type not in valid_tasks:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de tarefa inválido: {request.task_type}. Use: {', '.join(valid_tasks)}",
            )

        kwargs = {}
        if request.task_type == "s3_cleanup":
            kwargs["older_than_hours"] = request.older_than_hours

        job_id = redis_queue_service.enqueue_cleanup_task(
            task_type=request.task_type, **kwargs
        )

        return {
            "message": f"Tarefa de limpeza enfileirada: {request.task_type}",
            "job_id": job_id,
            "task_type": request.task_type,
            "status": "queued",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao enfileirar tarefa de limpeza: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.get("/health")
async def queue_health():
    """
    Health check das filas Redis

    Returns:
        dict: Status das filas
    """
    try:
        document_info = redis_queue_service.get_queue_info("document_processing")
        cleanup_info = redis_queue_service.get_queue_info("cleanup_tasks")

        return {
            "status": "healthy",
            "queues": {
                "document_processing": {
                    "available": bool(document_info),
                    "length": document_info.get("length", 0) if document_info else 0,
                    "failed": (
                        document_info.get("failed_count", 0) if document_info else 0
                    ),
                },
                "cleanup_tasks": {
                    "available": bool(cleanup_info),
                    "length": cleanup_info.get("length", 0) if cleanup_info else 0,
                    "failed": (
                        cleanup_info.get("failed_count", 0) if cleanup_info else 0
                    ),
                },
            },
            "timestamp": "2024-01-15T10:30:00Z",
        }

    except Exception as e:
        logger.error(f"Erro no health check das filas: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
