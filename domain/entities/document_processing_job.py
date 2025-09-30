from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import UUID, uuid4

from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.content_hash import ContentHash
from domain.value_objects.processing_status import ProcessingStatus


@dataclass
class DocumentProcessingJob:
    """Entidade para gerenciar job de processamento de documento"""

    id: UUID = field(default_factory=uuid4)
    document_id: UUID = field(default_factory=uuid4)
    upload_id: UUID = field(default_factory=uuid4)
    status: ProcessingStatus = ProcessingStatus.UPLOADED
    current_step: str = ""
    progress: int = 0
    chunks_processed: int = 0
    total_chunks: int = 0
    processing_time_seconds: int = 0
    s3_file_deleted: bool = False
    duplicate_of: Optional[UUID] = None
    content_hash: Optional[ContentHash] = None
    error_message: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        self._validate_business_rules()
        self._sync_progress_with_status()

    def _validate_business_rules(self):
        """Valida regras de negócio do DocumentProcessingJob"""
        if self.progress < 0 or self.progress > 100:
            raise BusinessRuleViolationError("Progresso deve estar entre 0 e 100")

        if self.chunks_processed < 0:
            raise BusinessRuleViolationError("Chunks processados não pode ser negativo")

        if self.total_chunks < 0:
            raise BusinessRuleViolationError("Total de chunks não pode ser negativo")

        if self.chunks_processed > self.total_chunks and self.total_chunks > 0:
            raise BusinessRuleViolationError(
                "Chunks processados não pode exceder o total"
            )

        if self.processing_time_seconds < 0:
            raise BusinessRuleViolationError(
                "Tempo de processamento não pode ser negativo"
            )

    def _sync_progress_with_status(self):
        """Sincroniza progresso com status"""
        if not self.current_step:
            self.current_step = self.status.description

        if self.progress == 0 or self.progress == self.status.progress_percentage:
            self.progress = self.status.progress_percentage

    @classmethod
    def create(
        cls,
        document_id: UUID,
        upload_id: UUID,
        initial_step: str = "Iniciando processamento...",
    ) -> "DocumentProcessingJob":
        """Factory method para criar novo job de processamento"""
        return cls(
            document_id=document_id,
            upload_id=upload_id,
            current_step=initial_step,
            started_at=datetime.now(timezone.utc),
        )

    def update_status(
        self,
        status: ProcessingStatus,
        current_step: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Atualiza status do processamento"""
        old_status = self.status
        self.status = status

        if current_step:
            self.current_step = current_step
        else:
            self.current_step = status.description

        self.progress = status.progress_percentage

        if error_message:
            self.error_message = error_message

        if (
            old_status == ProcessingStatus.UPLOADED
            and status != ProcessingStatus.UPLOADED
        ):
            if not self.started_at:
                self.started_at = datetime.now(timezone.utc)

        if status.is_final and not self.completed_at:
            self.completed_at = datetime.now(timezone.utc)
            self._calculate_processing_time()

    def update_chunks_progress(self, chunks_processed: int, total_chunks: int) -> None:
        """Atualiza progresso de chunks"""
        self.chunks_processed = chunks_processed
        self.total_chunks = total_chunks

        if self.status == ProcessingStatus.EMBEDDING and total_chunks > 0:
            chunk_progress = (chunks_processed / total_chunks) * 30
            base_progress = 55
            self.progress = min(100, int(base_progress + chunk_progress))

            self.current_step = (
                f"Gerando embeddings (batch {chunks_processed}/{total_chunks})..."
            )

    def mark_as_duplicate(self, duplicate_of: UUID) -> None:
        """Marca como documento duplicado"""
        self.status = ProcessingStatus.DUPLICATE
        self.duplicate_of = duplicate_of
        self.progress = 100
        self.current_step = "Documento duplicado detectado"
        self.completed_at = datetime.utcnow()
        self._calculate_processing_time()

    def mark_s3_file_deleted(self) -> None:
        """Marca arquivo S3 como deletado"""
        self.s3_file_deleted = True
        self.metadata["s3_cleanup_at"] = datetime.now(timezone.utc).isoformat()

    def set_content_hash(self, content_hash: ContentHash) -> None:
        """Define hash do conteúdo"""
        self.content_hash = content_hash

    def fail_with_error(self, error_message: str) -> None:
        """Marca como falha com mensagem de erro"""
        self.status = ProcessingStatus.FAILED
        self.error_message = error_message
        self.progress = 0
        self.current_step = f"Erro: {error_message}"
        self.completed_at = datetime.now(timezone.utc)
        self._calculate_processing_time()

    def _calculate_processing_time(self) -> None:
        """Calcula tempo total de processamento"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            started = self.started_at
            completed = self.completed_at

            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)

            if completed.tzinfo is None:
                completed = completed.replace(tzinfo=timezone.utc)

            delta = completed - started
            self.processing_time_seconds = int(delta.total_seconds())

    @property
    def is_completed(self) -> bool:
        """Verifica se processamento foi concluído"""
        return self.status.is_final

    @property
    def is_processing(self) -> bool:
        """Verifica se está em processamento"""
        return self.status.is_processing

    @property
    def is_successful(self) -> bool:
        """Verifica se foi concluído com sucesso"""
        return self.status == ProcessingStatus.COMPLETED

    @property
    def is_duplicate(self) -> bool:
        """Verifica se é duplicata"""
        return self.status == ProcessingStatus.DUPLICATE

    @property
    def has_failed(self) -> bool:
        """Verifica se falhou"""
        return self.status == ProcessingStatus.FAILED

    @property
    def estimated_time_remaining(self) -> Optional[str]:
        """Estima tempo restante baseado no progresso"""
        if not self.started_at or self.progress == 0:
            return None

        elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        if self.progress >= 100:
            return "Concluído"

        estimated_total = elapsed / (self.progress / 100)
        remaining = estimated_total - elapsed

        if remaining <= 60:
            return f"{int(remaining)} segundos"
        elif remaining <= 3600:
            return f"{int(remaining / 60)} minutos"
        else:
            return f"{int(remaining / 3600)} horas"
