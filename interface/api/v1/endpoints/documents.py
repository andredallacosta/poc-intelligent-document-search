import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from application.dto.document_dto import (
    PresignedUploadRequestDTO,
    ProcessDocumentRequestDTO,
)
from application.use_cases.create_presigned_upload import CreatePresignedUploadUseCase
from application.use_cases.get_document_status import (
    GetDocumentStatusUseCase,
    GetJobStatusUseCase,
)
from application.use_cases.process_uploaded_document import (
    ProcessUploadedDocumentUseCase,
)
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from interface.schemas.documents import (
    DocumentError,
    DocumentHealth,
    DocumentListResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentStats,
    DocumentStatus,
    PresignedUploadRequest,
    PresignedUploadResponse,
    ProcessDocumentRequest,
    ProcessDocumentResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# === DEPENDENCY INJECTION ===
# NOTA: Estas dependências serão implementadas no container

async def get_create_presigned_upload_use_case() -> CreatePresignedUploadUseCase:
    """Dependency para CreatePresignedUploadUseCase"""
    # Será implementado no container
    from interface.dependencies.container import get_create_presigned_upload_use_case
    return await get_create_presigned_upload_use_case()


async def get_process_document_use_case() -> ProcessUploadedDocumentUseCase:
    """Dependency para ProcessUploadedDocumentUseCase"""
    # Será implementado no container
    from interface.dependencies.container import get_process_document_use_case
    return await get_process_document_use_case()


async def get_document_status_use_case() -> GetDocumentStatusUseCase:
    """Dependency para GetDocumentStatusUseCase"""
    # Será implementado no container
    from interface.dependencies.container import get_document_status_use_case
    return await get_document_status_use_case()


async def get_job_status_use_case() -> GetJobStatusUseCase:
    """Dependency para GetJobStatusUseCase"""
    # Será implementado no container
    from interface.dependencies.container import get_job_status_use_case
    return await get_job_status_use_case()


# === UPLOAD ENDPOINTS ===

@router.post(
    "/upload/presigned",
    response_model=PresignedUploadResponse,
    responses={
        400: {"model": DocumentError, "description": "Dados inválidos"},
        500: {"model": DocumentError, "description": "Erro interno"},
    },
    summary="Criar URL de upload presigned",
    description="Gera URL presigned para upload direto de arquivo ao S3. Suporta PDF, DOC e DOCX até 5GB.",
)
async def create_presigned_upload(
    request: PresignedUploadRequest,
    use_case: CreatePresignedUploadUseCase = Depends(get_create_presigned_upload_use_case),
):
    """Cria URL presigned para upload direto ao S3"""
    try:
        # Converter schema para DTO
        dto = PresignedUploadRequestDTO(
            filename=request.filename,
            file_size=request.file_size,
            content_type=request.content_type,
            title=request.title,
            description=request.description,
            tags=request.tags or [],
        )
        
        # Executar use case
        result = await use_case.execute(dto)
        
        # Converter DTO para schema de resposta
        return PresignedUploadResponse(
            upload_url=result.upload_url,
            document_id=result.document_id,
            upload_id=result.upload_id,
            expires_in=result.expires_in,
            expires_at=result.expires_at,
        )
        
    except BusinessRuleViolationError as e:
        logger.warning(f"Erro de validação no upload presigned: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro interno no upload presigned: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@router.post(
    "/{document_id}/process",
    response_model=ProcessDocumentResponse,
    responses={
        400: {"model": DocumentError, "description": "Upload inválido"},
        404: {"model": DocumentError, "description": "Upload não encontrado"},
        500: {"model": DocumentError, "description": "Erro interno"},
    },
    summary="Processar documento após upload",
    description="Inicia processamento de documento após upload para S3. Inclui extração de texto, chunking e geração de embeddings.",
)
async def process_document(
    document_id: UUID,
    request: ProcessDocumentRequest,
    use_case: ProcessUploadedDocumentUseCase = Depends(get_process_document_use_case),
):
    """Processa documento após upload"""
    try:
        # Converter schema para DTO
        dto = ProcessDocumentRequestDTO(
            upload_id=request.upload_id,
            file_hash=request.file_hash,
        )
        
        # Executar use case
        result = await use_case.execute(dto)
        
        # Converter DTO para schema de resposta
        return ProcessDocumentResponse(
            job_id=result.job_id,
            status=result.status.value,
            estimated_time=result.estimated_time,
        )
        
    except BusinessRuleViolationError as e:
        logger.warning(f"Erro de validação no processamento: {e}")
        if "não encontrado" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro interno no processamento: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


# === STATUS ENDPOINTS ===

@router.get(
    "/{document_id}/status",
    response_model=DocumentStatus,
    responses={
        404: {"model": DocumentError, "description": "Documento não encontrado"},
        500: {"model": DocumentError, "description": "Erro interno"},
    },
    summary="Obter status do documento",
    description="Consulta status atual do processamento de um documento, incluindo progresso e tempo estimado.",
)
async def get_document_status(
    document_id: UUID,
    use_case: GetDocumentStatusUseCase = Depends(get_document_status_use_case),
):
    """Obtém status de processamento do documento"""
    try:
        # Executar use case
        result = await use_case.execute(document_id)
        
        # Converter DTO para schema de resposta
        return DocumentStatus(
            document_id=result.document_id,
            job_id=result.job_id,
            status=result.status.value,
            progress=result.progress,
            current_step=result.current_step,
            chunks_processed=result.chunks_processed,
            total_chunks=result.total_chunks,
            processing_time=result.processing_time,
            s3_file_deleted=result.s3_file_deleted,
            duplicate_of=result.duplicate_of,
            error=result.error,
            estimated_time_remaining=result.estimated_time_remaining,
        )
        
    except BusinessRuleViolationError as e:
        logger.warning(f"Erro ao obter status do documento: {e}")
        if "não encontrado" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro interno ao obter status: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@router.get(
    "/jobs/{job_id}/status",
    response_model=DocumentStatus,
    responses={
        404: {"model": DocumentError, "description": "Job não encontrado"},
        500: {"model": DocumentError, "description": "Erro interno"},
    },
    summary="Obter status do job",
    description="Consulta status atual de um job de processamento específico.",
)
async def get_job_status(
    job_id: UUID,
    use_case: GetJobStatusUseCase = Depends(get_job_status_use_case),
):
    """Obtém status de job de processamento"""
    try:
        # Executar use case
        result = await use_case.execute(job_id)
        
        # Converter DTO para schema de resposta
        return DocumentStatus(
            document_id=result.document_id,
            job_id=result.job_id,
            status=result.status.value,
            progress=result.progress,
            current_step=result.current_step,
            chunks_processed=result.chunks_processed,
            total_chunks=result.total_chunks,
            processing_time=result.processing_time,
            s3_file_deleted=result.s3_file_deleted,
            duplicate_of=result.duplicate_of,
            error=result.error,
            estimated_time_remaining=result.estimated_time_remaining,
        )
        
    except BusinessRuleViolationError as e:
        logger.warning(f"Erro ao obter status do job: {e}")
        if "não encontrado" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro interno ao obter status do job: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


# === SEARCH ENDPOINTS ===

@router.post(
    "/search",
    response_model=DocumentSearchResponse,
    responses={
        400: {"model": DocumentError, "description": "Consulta inválida"},
        500: {"model": DocumentError, "description": "Erro interno"},
    },
    summary="Busca semântica em documentos",
    description="Realiza busca semântica nos documentos indexados usando embeddings vetoriais.",
)
async def search_documents(request: DocumentSearchRequest):
    """Busca semântica em documentos"""
    # NOTA: Implementação será adicionada posteriormente
    # Por enquanto, retornar resposta vazia
    return DocumentSearchResponse(
        results=[],
        query_time=0.0,
        total_chunks_searched=0,
    )


# === MANAGEMENT ENDPOINTS ===

@router.get(
    "",
    response_model=DocumentListResponse,
    summary="Listar documentos",
    description="Lista documentos com filtros e paginação.",
)
async def list_documents(
    search: str = Query(None, description="Termo de busca"),
    tags: List[str] = Query(None, description="Filtrar por tags"),
    status: str = Query(None, description="Filtrar por status"),
    limit: int = Query(20, ge=1, le=100, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
):
    """Lista documentos com filtros"""
    # NOTA: Implementação será adicionada posteriormente
    return DocumentListResponse(
        documents=[],
        total=0,
        has_more=False,
    )


@router.get(
    "/{document_id}",
    response_model=dict,
    responses={
        404: {"model": DocumentError, "description": "Documento não encontrado"},
    },
    summary="Obter documento específico",
    description="Obtém detalhes completos de um documento específico.",
)
async def get_document(document_id: UUID):
    """Obtém documento específico"""
    # NOTA: Implementação será adicionada posteriormente
    raise HTTPException(status_code=404, detail="Documento não encontrado")


# === STATS ENDPOINTS ===

@router.get(
    "/stats",
    response_model=DocumentStats,
    summary="Estatísticas de documentos",
    description="Obtém estatísticas gerais dos documentos e processamento.",
)
async def get_document_stats():
    """Obtém estatísticas de documentos"""
    # NOTA: Implementação será adicionada posteriormente
    return DocumentStats(
        total_documents=0,
        by_status={},
        total_chunks=0,
        total_embeddings=0,
        storage_used_mb=0,
        processing_stats={},
        by_type={},
        by_content_type={},
    )


@router.get(
    "/health",
    response_model=DocumentHealth,
    summary="Health check de documentos",
    description="Verifica saúde dos serviços relacionados a documentos.",
)
async def get_document_health():
    """Health check específico de documentos"""
    # NOTA: Implementação será adicionada posteriormente
    return DocumentHealth(
        status="healthy",
        database="connected",
        vector_store="connected",
        s3="connected",
        openai="connected",
        processing_queue=0,
        last_successful_upload=None,
    )
