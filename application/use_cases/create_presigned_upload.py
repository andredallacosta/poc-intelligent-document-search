import logging
from datetime import datetime, timedelta
from uuid import uuid4

from application.dto.document_dto import (
    PresignedUploadRequestDTO,
    PresignedUploadResponseDTO,
)
from domain.entities.file_upload import FileUpload
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.repositories.file_upload_repository import FileUploadRepository
from domain.value_objects.s3_key import S3Key
from infrastructure.external.s3_service import S3Service

logger = logging.getLogger(__name__)


class CreatePresignedUploadUseCase:
    """Use case para criar upload presigned S3"""
    
    def __init__(
        self,
        s3_service: S3Service,
        file_upload_repository: FileUploadRepository
    ):
        self.s3_service = s3_service
        self.file_upload_repository = file_upload_repository
    
    async def execute(self, request: PresignedUploadRequestDTO) -> PresignedUploadResponseDTO:
        """
        Cria URL presigned para upload direto ao S3
        
        Args:
            request: Dados da solicitação de upload
            
        Returns:
            PresignedUploadResponseDTO: URL e dados do upload
            
        Raises:
            BusinessRuleViolationError: Se dados inválidos ou erro S3
        """
        try:
            # Validar dados de entrada
            self._validate_request(request)
            
            # Criar FileUpload
            document_id = uuid4()
            file_upload = FileUpload.create(
                filename=request.filename,
                file_size=request.file_size,
                content_type=request.content_type,
                document_id=document_id
            )
            
            # Gerar chave S3 temporária
            s3_key = S3Key.create_temp_key(
                document_id=str(document_id),
                filename=request.filename
            )
            
            # Gerar URL presigned
            upload_url, expires_at = self.s3_service.generate_presigned_upload_url(
                s3_key=s3_key,
                content_type=request.content_type,
                expires_in=3600  # 1 hora
            )
            
            # Atualizar FileUpload com dados S3
            file_upload.set_s3_info(s3_key, upload_url, expires_at)
            
            # Salvar no repositório
            await self.file_upload_repository.save(file_upload)
            
            logger.info(f"Upload presigned criado: {file_upload.id} -> {s3_key.key}")
            
            return PresignedUploadResponseDTO(
                upload_url=upload_url,
                document_id=document_id,
                upload_id=file_upload.id,
                expires_in=3600,
                expires_at=expires_at
            )
            
        except BusinessRuleViolationError:
            raise
        except Exception as e:
            logger.error(f"Erro ao criar upload presigned: {e}")
            raise BusinessRuleViolationError(f"Falha na criação do upload: {str(e)}")
    
    def _validate_request(self, request: PresignedUploadRequestDTO) -> None:
        """Valida dados da solicitação"""
        if not request.filename or len(request.filename.strip()) == 0:
            raise BusinessRuleViolationError("Nome do arquivo é obrigatório")
        
        if request.file_size <= 0:
            raise BusinessRuleViolationError("Tamanho do arquivo deve ser maior que zero")
        
        if request.file_size > 5 * 1024 * 1024 * 1024:  # 5GB
            raise BusinessRuleViolationError("Arquivo não pode ser maior que 5GB")
        
        # Validar tipos de arquivo permitidos
        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
            "application/msword"  # .doc
        ]
        
        if request.content_type not in allowed_types:
            raise BusinessRuleViolationError(
                f"Tipo de arquivo não suportado: {request.content_type}. "
                f"Tipos permitidos: PDF, DOC, DOCX"
            )
        
        # Validar extensão do arquivo
        allowed_extensions = [".pdf", ".doc", ".docx"]
        file_ext = "." + request.filename.split(".")[-1].lower() if "." in request.filename else ""
        
        if file_ext not in allowed_extensions:
            raise BusinessRuleViolationError(
                f"Extensão de arquivo não suportada: {file_ext}. "
                f"Extensões permitidas: {', '.join(allowed_extensions)}"
            )
        
        # Validar título se fornecido
        if request.title and len(request.title) > 255:
            raise BusinessRuleViolationError("Título não pode ter mais de 255 caracteres")
        
        # Validar descrição se fornecida
        if request.description and len(request.description) > 1000:
            raise BusinessRuleViolationError("Descrição não pode ter mais de 1000 caracteres")
        
        # Validar tags se fornecidas
        if request.tags:
            if len(request.tags) > 10:
                raise BusinessRuleViolationError("Máximo de 10 tags permitidas")
            
            for tag in request.tags:
                if len(tag) > 50:
                    raise BusinessRuleViolationError("Tags não podem ter mais de 50 caracteres")
        
        logger.info(f"Solicitação validada: {request.filename} ({request.file_size} bytes)")
