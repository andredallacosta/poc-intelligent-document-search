from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from domain.entities.file_upload import FileUpload


class FileUploadRepository(ABC):
    """Interface do repositório de FileUpload"""
    
    @abstractmethod
    async def save(self, file_upload: FileUpload) -> None:
        """Salva um FileUpload"""
        pass
    
    @abstractmethod
    async def find_by_id(self, upload_id: UUID) -> Optional[FileUpload]:
        """Busca FileUpload por ID"""
        pass
    
    @abstractmethod
    async def find_by_document_id(self, document_id: UUID) -> Optional[FileUpload]:
        """Busca FileUpload por document_id"""
        pass
    
    @abstractmethod
    async def delete(self, upload_id: UUID) -> bool:
        """Remove FileUpload"""
        pass
