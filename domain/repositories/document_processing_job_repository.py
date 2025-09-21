from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from domain.entities.document_processing_job import DocumentProcessingJob
from domain.value_objects.processing_status import ProcessingStatus


class DocumentProcessingJobRepository(ABC):
    """Interface do repositório de DocumentProcessingJob"""
    
    @abstractmethod
    async def save(self, job: DocumentProcessingJob) -> None:
        """Salva um DocumentProcessingJob"""
        pass
    
    @abstractmethod
    async def find_by_id(self, job_id: UUID) -> Optional[DocumentProcessingJob]:
        """Busca job por ID"""
        pass
    
    @abstractmethod
    async def find_by_document_id(self, document_id: UUID) -> Optional[DocumentProcessingJob]:
        """Busca job por document_id"""
        pass
    
    @abstractmethod
    async def find_by_upload_id(self, upload_id: UUID) -> Optional[DocumentProcessingJob]:
        """Busca job por upload_id"""
        pass
    
    @abstractmethod
    async def find_by_status(self, status: ProcessingStatus, limit: int = 100) -> List[DocumentProcessingJob]:
        """Busca jobs por status"""
        pass
    
    @abstractmethod
    async def find_processing_jobs(self, limit: int = 100) -> List[DocumentProcessingJob]:
        """Busca jobs em processamento"""
        pass
    
    @abstractmethod
    async def delete(self, job_id: UUID) -> bool:
        """Remove job"""
        pass
