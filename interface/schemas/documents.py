from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PresignedUploadRequest(BaseModel):
    """Schema para solicitação de upload presigned"""

    filename: str = Field(
        ..., min_length=1, max_length=255, description="Nome do arquivo"
    )
    file_size: int = Field(
        ..., gt=0, le=5368709120, description="Tamanho do arquivo em bytes (máx 5GB)"
    )
    content_type: str = Field(..., description="Tipo MIME do arquivo")
    title: Optional[str] = Field(
        None, max_length=255, description="Título do documento"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Descrição do documento"
    )
    tags: Optional[List[str]] = Field(
        default_factory=list, description="Tags do documento"
    )

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v):
        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ]
        if v not in allowed_types:
            raise ValueError(f"Tipo de arquivo não suportado: {v}")
        return v

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v):
        allowed_extensions = [".pdf", ".doc", ".docx"]
        file_ext = "." + v.split(".")[-1].lower() if "." in v else ""
        if file_ext not in allowed_extensions:
            raise ValueError(f"Extensão não suportada: {file_ext}")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        if v and len(v) > 10:
            raise ValueError("Máximo de 10 tags permitidas")
        if v:
            for tag in v:
                if len(tag) > 50:
                    raise ValueError("Tags não podem ter mais de 50 caracteres")
        return v


class PresignedUploadResponse(BaseModel):
    """Schema para resposta de upload presigned"""

    upload_url: str = Field(..., description="URL para upload direto ao S3")
    document_id: UUID = Field(..., description="ID do documento")
    upload_id: UUID = Field(..., description="ID do upload")
    expires_in: int = Field(..., description="Tempo de expiração em segundos")
    expires_at: datetime = Field(..., description="Data/hora de expiração")
    upload_fields: Dict[str, str] = Field(
        ..., description="Campos necessários para presigned POST"
    )


class ProcessDocumentRequest(BaseModel):
    """Schema para solicitação de processamento"""

    upload_id: UUID = Field(..., description="ID do upload")
    file_hash: Optional[str] = Field(
        None, description="Hash SHA256 do arquivo (opcional)"
    )


class ProcessDocumentResponse(BaseModel):
    """Schema para resposta de processamento"""

    job_id: UUID = Field(..., description="ID do job de processamento")
    status: str = Field(..., description="Status atual do processamento")
    estimated_time: str = Field(..., description="Tempo estimado de processamento")


class DocumentStatus(BaseModel):
    """Schema para status de processamento"""

    document_id: UUID = Field(..., description="ID do documento")
    job_id: UUID = Field(..., description="ID do job")
    status: str = Field(..., description="Status atual")
    progress: int = Field(..., ge=0, le=100, description="Progresso em porcentagem")
    current_step: str = Field(..., description="Etapa atual do processamento")
    chunks_processed: int = Field(..., ge=0, description="Chunks processados")
    total_chunks: int = Field(..., ge=0, description="Total de chunks")
    processing_time: int = Field(
        ..., ge=0, description="Tempo de processamento em segundos"
    )
    s3_file_deleted: bool = Field(..., description="Se arquivo S3 foi removido")
    duplicate_of: Optional[UUID] = Field(
        None, description="ID do documento original se duplicata"
    )
    error: Optional[str] = Field(None, description="Mensagem de erro se houver")
    estimated_time_remaining: Optional[str] = Field(
        None, description="Tempo estimado restante"
    )


class DocumentSearchRequest(BaseModel):
    """Schema para busca semântica"""

    query: str = Field(
        ..., min_length=1, max_length=500, description="Consulta de busca"
    )
    n_results: int = Field(5, ge=1, le=20, description="Número de resultados")
    similarity_threshold: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Limite de similaridade (usa threshold adaptativo se não especificado)",
    )
    document_ids: Optional[List[UUID]] = Field(
        None, description="IDs específicos de documentos"
    )
    content_types: Optional[List[str]] = Field(
        None, description="Tipos de conteúdo para filtrar"
    )


class DocumentSearchResult(BaseModel):
    """Schema para resultado de busca"""

    chunk_id: UUID = Field(..., description="ID do chunk")
    document_id: UUID = Field(..., description="ID do documento")
    document_title: str = Field(..., description="Título do documento")
    content: str = Field(..., description="Conteúdo do chunk")
    similarity_score: float = Field(..., description="Score de similaridade")
    chunk_index: int = Field(..., description="Índice do chunk no documento")
    source: str = Field(..., description="Fonte do documento")
    metadata: Dict = Field(default_factory=dict, description="Metadados adicionais")


class DocumentSearchResponse(BaseModel):
    """Schema para resposta de busca"""

    results: List[DocumentSearchResult] = Field(..., description="Resultados da busca")
    query_time: float = Field(..., description="Tempo da consulta em segundos")
    total_chunks_searched: int = Field(..., description="Total de chunks pesquisados")


class DocumentListRequest(BaseModel):
    """Schema para listagem de documentos"""

    search: Optional[str] = Field(None, max_length=100, description="Termo de busca")
    tags: Optional[List[str]] = Field(None, description="Filtrar por tags")
    status: Optional[str] = Field(None, description="Filtrar por status")
    limit: int = Field(20, ge=1, le=100, description="Limite de resultados")
    offset: int = Field(0, ge=0, description="Offset para paginação")


class DocumentSummary(BaseModel):
    """Schema para resumo de documento"""

    id: UUID = Field(..., description="ID do documento")
    title: str = Field(..., description="Título")
    description: Optional[str] = Field(None, description="Descrição")
    tags: List[str] = Field(default_factory=list, description="Tags")
    content_type: str = Field(..., description="Tipo de conteúdo")
    status: str = Field(..., description="Status")
    file_size: int = Field(..., description="Tamanho do arquivo")
    chunk_count: int = Field(..., description="Número de chunks")
    word_count: int = Field(..., description="Número de palavras")
    language: str = Field(..., description="Idioma")
    created_at: datetime = Field(..., description="Data de criação")
    processed_at: Optional[datetime] = Field(None, description="Data de processamento")
    uploaded_by: Optional[str] = Field(None, description="Usuário que fez upload")
    usage_count: int = Field(..., description="Número de usos")


class DocumentListResponse(BaseModel):
    """Schema para resposta de listagem"""

    documents: List[DocumentSummary] = Field(..., description="Lista de documentos")
    total: int = Field(..., description="Total de documentos")
    has_more: bool = Field(..., description="Se há mais documentos")


class DocumentStats(BaseModel):
    """Schema para estatísticas"""

    total_documents: int = Field(..., description="Total de documentos")
    by_status: Dict[str, int] = Field(..., description="Documentos por status")
    total_chunks: int = Field(..., description="Total de chunks")
    total_embeddings: int = Field(..., description="Total de embeddings")
    storage_used_mb: int = Field(..., description="Armazenamento usado em MB")
    processing_stats: Dict[str, float] = Field(
        ..., description="Estatísticas de processamento"
    )
    by_type: Dict[str, int] = Field(..., description="Documentos por tipo de arquivo")
    by_content_type: Dict[str, int] = Field(
        ..., description="Documentos por tipo de conteúdo"
    )


class DocumentHealth(BaseModel):
    """Schema para health check"""

    status: str = Field(..., description="Status geral")
    database: str = Field(..., description="Status do banco")
    vector_store: str = Field(..., description="Status do vector store")
    s3: str = Field(..., description="Status do S3")
    openai: str = Field(..., description="Status da OpenAI")
    processing_queue: int = Field(..., description="Tamanho da fila de processamento")
    last_successful_upload: Optional[datetime] = Field(
        None, description="Último upload bem-sucedido"
    )


class DocumentError(BaseModel):
    """Schema para erros de documentos"""

    error: str = Field(..., description="Tipo do erro")
    detail: str = Field(..., description="Detalhes do erro")
    document_id: Optional[UUID] = Field(None, description="ID do documento relacionado")
    job_id: Optional[UUID] = Field(None, description="ID do job relacionado")
