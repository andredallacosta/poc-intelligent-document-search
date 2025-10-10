from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from application.dto.document_dto import (
    ProcessDocumentRequestDTO,
    ProcessDocumentResponseDTO,
)
from application.use_cases.process_uploaded_document import (
    ProcessUploadedDocumentUseCase,
)
from domain.entities.document_processing_job import DocumentProcessingJob
from domain.entities.file_upload import FileUpload
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.processing_status import ProcessingStatus
from domain.value_objects.s3_key import S3Key


class TestProcessUploadedDocumentUseCase:
    @pytest.fixture
    def mock_file_upload_repository(self):
        return Mock()

    @pytest.fixture
    def mock_job_repository(self):
        return Mock()

    @pytest.fixture
    def use_case(self, mock_file_upload_repository, mock_job_repository):
        return ProcessUploadedDocumentUseCase(
            file_upload_repository=mock_file_upload_repository,
            job_repository=mock_job_repository,
        )

    @pytest.fixture
    def sample_file_upload(self):
        return FileUpload(
            id=uuid4(),
            document_id=uuid4(),
            filename="test_document.pdf",
            content_type="application/pdf",
            file_size=1024000,
            s3_key=S3Key(bucket="test-bucket", key="uploads/test_document.pdf"),
        )

    @pytest.fixture
    def valid_request(self, sample_file_upload):
        return ProcessDocumentRequestDTO(upload_id=sample_file_upload.id)

    @pytest.mark.asyncio
    async def test_execute_success_new_job(
        self,
        use_case,
        valid_request,
        sample_file_upload,
        mock_file_upload_repository,
        mock_job_repository,
    ):
        mock_file_upload_repository.find_by_id = AsyncMock(
            return_value=sample_file_upload
        )
        mock_file_upload_repository.save = AsyncMock()
        mock_job_repository.find_by_upload_id = AsyncMock(return_value=None)
        mock_job_repository.save = AsyncMock()
        with patch(
            "application.use_cases.process_uploaded_document.redis_queue_service"
        ) as mock_redis:
            mock_redis.enqueue_document_processing.return_value = "redis_job_123"
            result = await use_case.execute(valid_request)
        assert isinstance(result, ProcessDocumentResponseDTO)
        assert result.status == ProcessingStatus.UPLOADED
        assert result.estimated_time == "2-5 minutos"
        assert result.job_id is not None
        mock_file_upload_repository.find_by_id.assert_called_once_with(
            valid_request.upload_id
        )
        mock_job_repository.find_by_upload_id.assert_called_once_with(
            valid_request.upload_id
        )
        mock_job_repository.save.assert_called()
        mock_redis.enqueue_document_processing.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_existing_job(
        self,
        use_case,
        valid_request,
        sample_file_upload,
        mock_file_upload_repository,
        mock_job_repository,
    ):
        existing_job = DocumentProcessingJob(
            id=uuid4(),
            document_id=sample_file_upload.document_id,
            upload_id=valid_request.upload_id,
            status=ProcessingStatus.EMBEDDING,
        )
        mock_file_upload_repository.find_by_id = AsyncMock(
            return_value=sample_file_upload
        )
        mock_job_repository.find_by_upload_id = AsyncMock(return_value=existing_job)
        result = await use_case.execute(valid_request)
        assert isinstance(result, ProcessDocumentResponseDTO)
        assert result.job_id == existing_job.id
        assert result.status == ProcessingStatus.EMBEDDING
        assert result.estimated_time == "2-4 minutos"
        mock_job_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_upload_not_found(
        self, use_case, valid_request, mock_file_upload_repository
    ):
        mock_file_upload_repository.find_by_id = AsyncMock(return_value=None)
        with pytest.raises(
            BusinessRuleViolationError,
            match=f"Upload não encontrado: {valid_request.upload_id}",
        ):
            await use_case.execute(valid_request)
        mock_file_upload_repository.find_by_id.assert_called_once_with(
            valid_request.upload_id
        )

    @pytest.mark.asyncio
    async def test_execute_upload_no_s3_key(
        self, use_case, valid_request, mock_file_upload_repository
    ):
        file_upload = FileUpload(
            id=valid_request.upload_id,
            document_id=uuid4(),
            filename="test.pdf",
            content_type="application/pdf",
            file_size=1024000,
            s3_key=None,
        )
        mock_file_upload_repository.find_by_id = AsyncMock(return_value=file_upload)
        with pytest.raises(
            BusinessRuleViolationError, match="Upload não possui chave S3"
        ):
            await use_case.execute(valid_request)

    @pytest.mark.asyncio
    async def test_execute_upload_expired(
        self, use_case, valid_request, mock_file_upload_repository
    ):
        expired_upload = FileUpload(
            id=valid_request.upload_id,
            document_id=uuid4(),
            filename="test.pdf",
            content_type="application/pdf",
            file_size=1024000,
            s3_key=S3Key(bucket="test-bucket", key="uploads/test.pdf"),
        )
        mock_file_upload_repository.find_by_id = AsyncMock(return_value=expired_upload)
        with patch(
            "domain.entities.file_upload.FileUpload.is_expired",
            new_callable=lambda: property(lambda self: True),
        ):
            with pytest.raises(BusinessRuleViolationError, match="Upload expirou"):
                await use_case.execute(valid_request)

    @pytest.mark.asyncio
    async def test_execute_redis_enqueue_failure(
        self,
        use_case,
        valid_request,
        sample_file_upload,
        mock_file_upload_repository,
        mock_job_repository,
    ):
        mock_file_upload_repository.find_by_id = AsyncMock(
            return_value=sample_file_upload
        )
        mock_file_upload_repository.save = AsyncMock()
        mock_job_repository.find_by_upload_id = AsyncMock(return_value=None)
        mock_job_repository.save = AsyncMock()
        with patch(
            "infrastructure.queue.redis_queue.redis_queue_service"
        ) as mock_redis:
            mock_redis.enqueue_document_processing.side_effect = Exception(
                "Redis connection failed"
            )
            with pytest.raises(
                BusinessRuleViolationError, match="Falha ao iniciar processamento"
            ):
                await use_case.execute(valid_request)
            assert mock_job_repository.save.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_repository_error(
        self, use_case, valid_request, mock_file_upload_repository
    ):
        mock_file_upload_repository.find_by_id = AsyncMock(
            side_effect=Exception("Database error")
        )
        with pytest.raises(BusinessRuleViolationError, match="Falha no processamento"):
            await use_case.execute(valid_request)

    def test_validate_upload_state_valid(self, use_case, sample_file_upload):
        with patch(
            "domain.entities.file_upload.FileUpload.is_expired",
            new_callable=lambda: property(lambda self: False),
        ):
            use_case._validate_upload_state(sample_file_upload)

    def test_validate_upload_state_no_s3_key(self, use_case):
        file_upload = FileUpload(
            id=uuid4(),
            document_id=uuid4(),
            filename="test.pdf",
            content_type="application/pdf",
            file_size=1024000,
            s3_key=None,
        )
        with pytest.raises(
            BusinessRuleViolationError, match="Upload não possui chave S3"
        ):
            use_case._validate_upload_state(file_upload)

    def test_validate_upload_state_expired(self, use_case, sample_file_upload):
        with patch(
            "domain.entities.file_upload.FileUpload.is_expired",
            new_callable=lambda: property(lambda self: True),
        ):
            with pytest.raises(BusinessRuleViolationError, match="Upload expirou"):
                use_case._validate_upload_state(sample_file_upload)

    def test_get_estimated_time_uploaded(self, use_case):
        result = use_case._get_estimated_time(ProcessingStatus.UPLOADED)
        assert result == "2-5 minutos"

    def test_get_estimated_time_extracting(self, use_case):
        result = use_case._get_estimated_time(ProcessingStatus.EXTRACTING)
        assert result == "1-3 minutos"

    def test_get_estimated_time_checking_duplicates(self, use_case):
        result = use_case._get_estimated_time(ProcessingStatus.CHECKING_DUPLICATES)
        assert result == "30 segundos"

    def test_get_estimated_time_chunking(self, use_case):
        result = use_case._get_estimated_time(ProcessingStatus.CHUNKING)
        assert result == "1-2 minutos"

    def test_get_estimated_time_embedding(self, use_case):
        result = use_case._get_estimated_time(ProcessingStatus.EMBEDDING)
        assert result == "2-4 minutos"

    def test_get_estimated_time_completed(self, use_case):
        result = use_case._get_estimated_time(ProcessingStatus.COMPLETED)
        assert result == "Concluído"

    def test_get_estimated_time_failed(self, use_case):
        result = use_case._get_estimated_time(ProcessingStatus.FAILED)
        assert result == "Falha"

    def test_get_estimated_time_duplicate(self, use_case):
        result = use_case._get_estimated_time(ProcessingStatus.DUPLICATE)
        assert result == "Concluído (duplicata)"

    @pytest.mark.asyncio
    async def test_execute_completed_existing_job(
        self,
        use_case,
        valid_request,
        sample_file_upload,
        mock_file_upload_repository,
        mock_job_repository,
    ):
        existing_job = DocumentProcessingJob(
            id=uuid4(),
            document_id=sample_file_upload.document_id,
            upload_id=valid_request.upload_id,
            status=ProcessingStatus.COMPLETED,
        )
        mock_file_upload_repository.find_by_id = AsyncMock(
            return_value=sample_file_upload
        )
        mock_job_repository.find_by_upload_id = AsyncMock(return_value=existing_job)
        result = await use_case.execute(valid_request)
        assert result.status == ProcessingStatus.COMPLETED
        assert result.estimated_time == "Concluído"

    @pytest.mark.asyncio
    async def test_execute_failed_existing_job(
        self,
        use_case,
        valid_request,
        sample_file_upload,
        mock_file_upload_repository,
        mock_job_repository,
    ):
        existing_job = DocumentProcessingJob(
            id=uuid4(),
            document_id=sample_file_upload.document_id,
            upload_id=valid_request.upload_id,
            status=ProcessingStatus.FAILED,
        )
        mock_file_upload_repository.find_by_id = AsyncMock(
            return_value=sample_file_upload
        )
        mock_job_repository.find_by_upload_id = AsyncMock(return_value=existing_job)
        result = await use_case.execute(valid_request)
        assert result.status == ProcessingStatus.FAILED
        assert result.estimated_time == "Falha"

    @pytest.mark.asyncio
    async def test_execute_duplicate_existing_job(
        self,
        use_case,
        valid_request,
        sample_file_upload,
        mock_file_upload_repository,
        mock_job_repository,
    ):
        existing_job = DocumentProcessingJob(
            id=uuid4(),
            document_id=sample_file_upload.document_id,
            upload_id=valid_request.upload_id,
            status=ProcessingStatus.DUPLICATE,
        )
        mock_file_upload_repository.find_by_id = AsyncMock(
            return_value=sample_file_upload
        )
        mock_job_repository.find_by_upload_id = AsyncMock(return_value=existing_job)
        result = await use_case.execute(valid_request)
        assert result.status == ProcessingStatus.DUPLICATE
        assert result.estimated_time == "Concluído (duplicata)"

    @pytest.mark.asyncio
    async def test_execute_job_creation_with_metadata(
        self,
        use_case,
        valid_request,
        sample_file_upload,
        mock_file_upload_repository,
        mock_job_repository,
    ):
        mock_file_upload_repository.find_by_id = AsyncMock(
            return_value=sample_file_upload
        )
        mock_file_upload_repository.save = AsyncMock()
        mock_job_repository.find_by_upload_id = AsyncMock(return_value=None)
        saved_jobs = []

        async def capture_save(job):
            saved_jobs.append(job)

        mock_job_repository.save = AsyncMock(side_effect=capture_save)
        with patch(
            "application.use_cases.process_uploaded_document.redis_queue_service"
        ) as mock_redis:
            mock_redis.enqueue_document_processing.return_value = "redis_job_456"
            await use_case.execute(valid_request)
        assert len(saved_jobs) == 2
        final_job = saved_jobs[1]
        assert "redis_job_id" in final_job.metadata
        assert final_job.metadata["redis_job_id"] == "redis_job_456"

    @pytest.mark.asyncio
    async def test_execute_file_upload_marked_uploaded(
        self,
        use_case,
        valid_request,
        sample_file_upload,
        mock_file_upload_repository,
        mock_job_repository,
    ):
        mock_file_upload_repository.find_by_id = AsyncMock(
            return_value=sample_file_upload
        )
        mock_job_repository.find_by_upload_id = AsyncMock(return_value=None)
        mock_job_repository.save = AsyncMock()
        saved_uploads = []

        async def capture_upload_save(upload):
            saved_uploads.append(upload)

        mock_file_upload_repository.save = AsyncMock(side_effect=capture_upload_save)
        with patch(
            "application.use_cases.process_uploaded_document.redis_queue_service"
        ) as mock_redis:
            mock_redis.enqueue_document_processing.return_value = "redis_job_789"
            await use_case.execute(valid_request)
        assert len(saved_uploads) == 1
        assert saved_uploads[0].uploaded_at is not None
