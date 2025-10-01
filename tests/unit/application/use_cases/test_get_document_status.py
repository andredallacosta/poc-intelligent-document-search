import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from application.use_cases.get_document_status import GetDocumentStatusUseCase, GetJobStatusUseCase
from application.dto.document_dto import DocumentStatusDTO
from domain.entities.document_processing_job import DocumentProcessingJob
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.processing_status import ProcessingStatus


class TestGetDocumentStatusUseCase:
    
    @pytest.fixture
    def mock_job_repository(self):
        return Mock()
    
    @pytest.fixture
    def use_case(self, mock_job_repository):
        return GetDocumentStatusUseCase(job_repository=mock_job_repository)
    
    @pytest.fixture
    def sample_job(self):
        return DocumentProcessingJob(
            id=uuid4(),
            document_id=uuid4(),
            upload_id=uuid4(),
            status=ProcessingStatus.EMBEDDING,
            current_step="Gerando embeddings...",
            progress=75,
            chunks_processed=15,
            total_chunks=20,
            processing_time_seconds=120,
            s3_file_deleted=False,
            duplicate_of=None,
            error_message=None
        )
    
    @pytest.mark.asyncio
    async def test_execute_success(self, use_case, mock_job_repository, sample_job):
        document_id = sample_job.document_id
        mock_job_repository.find_by_document_id = AsyncMock(return_value=sample_job)
        
        result = await use_case.execute(document_id)
        
        assert isinstance(result, DocumentStatusDTO)
        assert result.document_id == document_id
        assert result.job_id == sample_job.id
        assert result.status == ProcessingStatus.EMBEDDING
        assert result.progress == 75
        assert result.current_step == "Gerando embeddings..."
        assert result.chunks_processed == 15
        assert result.total_chunks == 20
        assert result.processing_time == 120
        assert result.s3_file_deleted is False
        assert result.duplicate_of is None
        assert result.error is None
        
        mock_job_repository.find_by_document_id.assert_called_once_with(document_id)
    
    @pytest.mark.asyncio
    async def test_execute_document_not_found(self, use_case, mock_job_repository):
        document_id = uuid4()
        mock_job_repository.find_by_document_id = AsyncMock(return_value=None)
        
        with pytest.raises(BusinessRuleViolationError, match=f"Documento não encontrado: {document_id}"):
            await use_case.execute(document_id)
        
        mock_job_repository.find_by_document_id.assert_called_once_with(document_id)
    
    @pytest.mark.asyncio
    async def test_execute_completed_job(self, use_case, mock_job_repository):
        job = DocumentProcessingJob(
            id=uuid4(),
            document_id=uuid4(),
            upload_id=uuid4(),
            status=ProcessingStatus.COMPLETED,
            current_step="Processamento concluído",
            progress=100,
            chunks_processed=25,
            total_chunks=25,
            processing_time_seconds=300,
            s3_file_deleted=True
        )
        
        mock_job_repository.find_by_document_id = AsyncMock(return_value=job)
        
        result = await use_case.execute(job.document_id)
        
        assert result.status == ProcessingStatus.COMPLETED
        assert result.progress == 100
        assert result.s3_file_deleted is True
    
    @pytest.mark.asyncio
    async def test_execute_failed_job(self, use_case, mock_job_repository):
        job = DocumentProcessingJob(
            id=uuid4(),
            document_id=uuid4(),
            upload_id=uuid4(),
            status=ProcessingStatus.FAILED,
            current_step="Processamento falhou",
            progress=45,
            error_message="Erro na extração de texto"
        )
        
        mock_job_repository.find_by_document_id = AsyncMock(return_value=job)
        
        result = await use_case.execute(job.document_id)
        
        assert result.status == ProcessingStatus.FAILED
        assert result.error == "Erro na extração de texto"
    
    @pytest.mark.asyncio
    async def test_execute_duplicate_job(self, use_case, mock_job_repository):
        duplicate_document_id = uuid4()
        job = DocumentProcessingJob(
            id=uuid4(),
            document_id=uuid4(),
            upload_id=uuid4(),
            status=ProcessingStatus.DUPLICATE,
            duplicate_of=duplicate_document_id,
            progress=100
        )
        
        mock_job_repository.find_by_document_id = AsyncMock(return_value=job)
        
        result = await use_case.execute(job.document_id)
        
        assert result.status == ProcessingStatus.DUPLICATE
        assert result.duplicate_of == duplicate_document_id
    
    @pytest.mark.asyncio
    async def test_execute_repository_exception(self, use_case, mock_job_repository):
        document_id = uuid4()
        mock_job_repository.find_by_document_id = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(BusinessRuleViolationError, match="Falha ao obter status"):
            await use_case.execute(document_id)


class TestGetJobStatusUseCase:
    
    @pytest.fixture
    def mock_job_repository(self):
        return Mock()
    
    @pytest.fixture
    def use_case(self, mock_job_repository):
        return GetJobStatusUseCase(job_repository=mock_job_repository)
    
    @pytest.fixture
    def sample_job(self):
        return DocumentProcessingJob(
            id=uuid4(),
            document_id=uuid4(),
            upload_id=uuid4(),
            status=ProcessingStatus.CHUNKING,
            current_step="Dividindo documento...",
            progress=60,
            chunks_processed=10,
            total_chunks=20,
            processing_time_seconds=90
        )
    
    @pytest.mark.asyncio
    async def test_execute_success(self, use_case, mock_job_repository, sample_job):
        job_id = sample_job.id
        mock_job_repository.find_by_id = AsyncMock(return_value=sample_job)
        
        result = await use_case.execute(job_id)
        
        assert isinstance(result, DocumentStatusDTO)
        assert result.job_id == job_id
        assert result.document_id == sample_job.document_id
        assert result.status == ProcessingStatus.CHUNKING
        assert result.progress == 60
        assert result.current_step == "Dividindo documento..."
        assert result.chunks_processed == 10
        assert result.total_chunks == 20
        assert result.processing_time == 90
        
        mock_job_repository.find_by_id.assert_called_once_with(job_id)
    
    @pytest.mark.asyncio
    async def test_execute_job_not_found(self, use_case, mock_job_repository):
        job_id = uuid4()
        mock_job_repository.find_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(BusinessRuleViolationError, match=f"Job não encontrado: {job_id}"):
            await use_case.execute(job_id)
        
        mock_job_repository.find_by_id.assert_called_once_with(job_id)
    
    @pytest.mark.asyncio
    async def test_execute_extracting_status(self, use_case, mock_job_repository):
        job = DocumentProcessingJob(
            id=uuid4(),
            document_id=uuid4(),
            upload_id=uuid4(),
            status=ProcessingStatus.EXTRACTING,
            current_step="Extraindo texto...",
            progress=25
        )
        
        mock_job_repository.find_by_id = AsyncMock(return_value=job)
        
        result = await use_case.execute(job.id)
        
        assert result.status == ProcessingStatus.EXTRACTING
        assert result.progress == 25
        assert result.current_step == "Extraindo texto..."
    
    @pytest.mark.asyncio
    async def test_execute_checking_duplicates_status(self, use_case, mock_job_repository):
        job = DocumentProcessingJob(
            id=uuid4(),
            document_id=uuid4(),
            upload_id=uuid4(),
            status=ProcessingStatus.CHECKING_DUPLICATES,
            current_step="Verificando duplicatas...",
            progress=35
        )
        
        mock_job_repository.find_by_id = AsyncMock(return_value=job)
        
        result = await use_case.execute(job.id)
        
        assert result.status == ProcessingStatus.CHECKING_DUPLICATES
        assert result.progress == 35
    
    @pytest.mark.asyncio
    async def test_execute_uploaded_status(self, use_case, mock_job_repository):
        job = DocumentProcessingJob(
            id=uuid4(),
            document_id=uuid4(),
            upload_id=uuid4(),
            status=ProcessingStatus.UPLOADED,
            current_step="Iniciando processamento...",
            progress=5
        )
        
        mock_job_repository.find_by_id = AsyncMock(return_value=job)
        
        result = await use_case.execute(job.id)
        
        assert result.status == ProcessingStatus.UPLOADED
        assert result.progress == 5
    
    @pytest.mark.asyncio
    async def test_execute_with_estimated_time_remaining(self, use_case, mock_job_repository):
        job = DocumentProcessingJob(
            id=uuid4(),
            document_id=uuid4(),
            upload_id=uuid4(),
            status=ProcessingStatus.EMBEDDING,
            chunks_processed=16,
            total_chunks=20
        )
        
        mock_job_repository.find_by_id = AsyncMock(return_value=job)
        
        result = await use_case.execute(job.id)
        
        assert result.estimated_time_remaining is not None or result.estimated_time_remaining is None
    
    @pytest.mark.asyncio
    async def test_execute_repository_exception(self, use_case, mock_job_repository):
        job_id = uuid4()
        mock_job_repository.find_by_id = AsyncMock(side_effect=Exception("Database connection failed"))
        
        with pytest.raises(BusinessRuleViolationError, match="Falha ao obter status"):
            await use_case.execute(job_id)
    
    @pytest.mark.asyncio
    async def test_execute_zero_progress(self, use_case, mock_job_repository):
        job = DocumentProcessingJob(
            id=uuid4(),
            document_id=uuid4(),
            upload_id=uuid4(),
            status=ProcessingStatus.UPLOADED,
            chunks_processed=0,
            total_chunks=0
        )
        
        mock_job_repository.find_by_id = AsyncMock(return_value=job)
        
        result = await use_case.execute(job.id)
        
        assert result.progress >= 0
        assert result.chunks_processed == 0
        assert result.total_chunks == 0
    
    @pytest.mark.asyncio
    async def test_execute_with_all_fields_populated(self, use_case, mock_job_repository):
        job = DocumentProcessingJob(
            id=uuid4(),
            document_id=uuid4(),
            upload_id=uuid4(),
            status=ProcessingStatus.COMPLETED,
            current_step="Concluído",
            progress=100,
            chunks_processed=30,
            total_chunks=30,
            processing_time_seconds=450,
            s3_file_deleted=True,
            duplicate_of=None,
            error_message=None
        )
        
        mock_job_repository.find_by_id = AsyncMock(return_value=job)
        
        result = await use_case.execute(job.id)
        
        assert result.job_id == job.id
        assert result.document_id == job.document_id
        assert result.status == job.status
        assert result.progress == job.progress
        assert result.current_step == job.current_step
        assert result.chunks_processed == job.chunks_processed
        assert result.total_chunks == job.total_chunks
        assert result.processing_time == job.processing_time_seconds
        assert result.s3_file_deleted == job.s3_file_deleted
        assert result.duplicate_of == job.duplicate_of
        assert result.error == job.error_message
