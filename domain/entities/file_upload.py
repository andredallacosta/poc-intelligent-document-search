from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.s3_key import S3Key


@dataclass
class FileUpload:
    """Entidade para gerenciar upload de arquivos"""
    
    id: UUID = field(default_factory=uuid4)
    document_id: UUID = field(default_factory=uuid4)
    filename: str = ""
    file_size: int = 0
    content_type: str = ""
    s3_key: Optional[S3Key] = None
    upload_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    uploaded_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        self._validate_business_rules()
    
    def _validate_business_rules(self):
        """Valida regras de negócio do FileUpload"""
        if self.filename and len(self.filename) > 255:
            raise BusinessRuleViolationError("Nome do arquivo não pode ter mais de 255 caracteres")
        
        if self.file_size < 0:
            raise BusinessRuleViolationError("Tamanho do arquivo não pode ser negativo")
        
        # Validar tamanho máximo (5GB - limite S3)
        max_size = 5 * 1024 * 1024 * 1024  # 5GB
        if self.file_size > max_size:
            raise BusinessRuleViolationError("Arquivo não pode ser maior que 5GB")
        
        # Validar tipos de conteúdo permitidos
        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
            "application/msword"  # .doc
        ]
        
        if self.content_type and self.content_type not in allowed_types:
            raise BusinessRuleViolationError(
                f"Tipo de arquivo não suportado: {self.content_type}. "
                f"Tipos permitidos: PDF, DOC, DOCX"
            )
    
    @classmethod
    def create(
        cls,
        filename: str,
        file_size: int,
        content_type: str,
        document_id: Optional[UUID] = None
    ) -> "FileUpload":
        """Factory method para criar novo FileUpload"""
        return cls(
            document_id=document_id or uuid4(),
            filename=filename.strip(),
            file_size=file_size,
            content_type=content_type,
        )
    
    def set_s3_info(self, s3_key: S3Key, upload_url: str, expires_at: datetime) -> None:
        """Define informações do S3 para upload"""
        self.s3_key = s3_key
        self.upload_url = upload_url
        self.expires_at = expires_at
    
    def mark_uploaded(self) -> None:
        """Marca como upload concluído"""
        self.uploaded_at = datetime.utcnow()
    
    @property
    def is_uploaded(self) -> bool:
        """Verifica se upload foi concluído"""
        return self.uploaded_at is not None
    
    @property
    def is_expired(self) -> bool:
        """Verifica se URL de upload expirou"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def file_extension(self) -> str:
        """Retorna extensão do arquivo"""
        if not self.filename:
            return ""
        
        parts = self.filename.split(".")
        if len(parts) > 1:
            return f".{parts[-1].lower()}"
        return ""
    
    @property
    def is_pdf(self) -> bool:
        """Verifica se é arquivo PDF"""
        return self.content_type == "application/pdf"
    
    @property
    def is_docx(self) -> bool:
        """Verifica se é arquivo DOCX"""
        return self.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    
    @property
    def is_doc(self) -> bool:
        """Verifica se é arquivo DOC legado"""
        return self.content_type == "application/msword"
