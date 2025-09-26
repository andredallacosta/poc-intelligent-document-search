from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from domain.value_objects.processing_status import ProcessingStatus


@dataclass
class PresignedUploadRequestDTO:
    """DTO para solicitação de upload presigned"""
    filename: str
    file_size: int
    content_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class PresignedUploadResponseDTO:
    """DTO para resposta de upload presigned"""
    upload_url: str
    document_id: UUID
    upload_id: UUID
    expires_in: int
    expires_at: datetime
    upload_fields: Dict[str, str]


@dataclass
class ProcessDocumentRequestDTO:
    """DTO para solicitação de processamento"""
    upload_id: UUID
    file_hash: Optional[str] = None


@dataclass
class ProcessDocumentResponseDTO:
    """DTO para resposta de processamento"""
    job_id: UUID
    status: ProcessingStatus
    estimated_time: str


@dataclass
class DocumentStatusDTO:
    """DTO para status de processamento"""
    document_id: UUID
    job_id: UUID
    status: ProcessingStatus
    progress: int
    current_step: str
    chunks_processed: int
    total_chunks: int
    processing_time: int
    s3_file_deleted: bool
    duplicate_of: Optional[UUID] = None
    error: Optional[str] = None
    estimated_time_remaining: Optional[str] = None


@dataclass
class DocumentSearchRequestDTO:
    """DTO para busca de documentos"""
    query: str
    n_results: int = 5
    similarity_threshold: float = 0.7
    document_ids: Optional[List[UUID]] = None
    content_types: Optional[List[str]] = None


@dataclass
class DocumentSearchResultDTO:
    """DTO para resultado de busca"""
    chunk_id: UUID
    document_id: UUID
    document_title: str
    content: str
    similarity_score: float
    chunk_index: int
    source: str
    metadata: Dict


@dataclass
class DocumentSearchResponseDTO:
    """DTO para resposta de busca"""
    results: List[DocumentSearchResultDTO]
    query_time: float
    total_chunks_searched: int


@dataclass
class DocumentListRequestDTO:
    """DTO para listagem de documentos"""
    search: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    limit: int = 20
    offset: int = 0


@dataclass
class DocumentSummaryDTO:
    """DTO para resumo de documento"""
    id: UUID
    title: str
    description: Optional[str]
    tags: List[str]
    content_type: str
    status: str
    file_size: int
    chunk_count: int
    word_count: int
    language: str
    created_at: datetime
    processed_at: Optional[datetime]
    uploaded_by: Optional[str]
    usage_count: int


@dataclass
class DocumentListResponseDTO:
    """DTO para resposta de listagem"""
    documents: List[DocumentSummaryDTO]
    total: int
    has_more: bool


@dataclass
class DocumentStatsDTO:
    """DTO para estatísticas de documentos"""
    total_documents: int
    by_status: Dict[str, int]
    total_chunks: int
    total_embeddings: int
    storage_used_mb: int
    processing_stats: Dict[str, float]
    by_type: Dict[str, int]
    by_content_type: Dict[str, int]


@dataclass
class DocumentHealthDTO:
    """DTO para health check de documentos"""
    status: str
    database: str
    vector_store: str
    s3: str
    openai: str
    processing_queue: int
    last_successful_upload: Optional[datetime]
