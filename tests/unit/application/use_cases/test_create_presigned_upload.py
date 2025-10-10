from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from application.dto.document_dto import (
    PresignedUploadRequestDTO,
    PresignedUploadResponseDTO,
)
from application.use_cases.create_presigned_upload import CreatePresignedUploadUseCase
from domain.exceptions.business_exceptions import BusinessRuleViolationError


class TestCreatePresignedUploadUseCase:
    @pytest.fixture
    def mock_s3_service(self):
        mock = Mock()
        mock.bucket = "test-bucket"
        mock.generate_presigned_upload_url = Mock()
        return mock

    @pytest.fixture
    def mock_file_upload_repository(self):
        return Mock()

    @pytest.fixture
    def use_case(self, mock_s3_service, mock_file_upload_repository):
        return CreatePresignedUploadUseCase(
            s3_service=mock_s3_service,
            file_upload_repository=mock_file_upload_repository,
        )

    @pytest.fixture
    def valid_request(self):
        return PresignedUploadRequestDTO(
            filename="test_document.pdf",
            file_size=1024000,
            content_type="application/pdf",
            title="Test Document",
            description="Test description",
            tags=["test", "document"],
        )

    @pytest.mark.asyncio
    async def test_execute_success(
        self, use_case, valid_request, mock_s3_service, mock_file_upload_repository
    ):
        upload_url = "https://test-bucket.s3.amazonaws.com/presigned-url"
        expires_at = datetime.now(timezone.utc)
        upload_fields = {"key": "value"}
        mock_s3_service.generate_presigned_upload_url.return_value = (
            upload_url,
            expires_at,
            upload_fields,
        )
        mock_file_upload_repository.save = AsyncMock()
        result = await use_case.execute(valid_request)
        assert isinstance(result, PresignedUploadResponseDTO)
        assert result.upload_url == upload_url
        assert result.expires_at == expires_at
        assert result.upload_fields == upload_fields
        assert result.expires_in == 3600
        assert result.document_id is not None
        assert result.upload_id is not None
        mock_s3_service.generate_presigned_upload_url.assert_called_once()
        mock_file_upload_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_minimal_request(
        self, use_case, mock_s3_service, mock_file_upload_repository
    ):
        minimal_request = PresignedUploadRequestDTO(
            filename="document.pdf", file_size=500000, content_type="application/pdf"
        )
        upload_url = "https://test-bucket.s3.amazonaws.com/presigned-url"
        expires_at = datetime.now(timezone.utc)
        upload_fields = {}
        mock_s3_service.generate_presigned_upload_url.return_value = (
            upload_url,
            expires_at,
            upload_fields,
        )
        mock_file_upload_repository.save = AsyncMock()
        result = await use_case.execute(minimal_request)
        assert isinstance(result, PresignedUploadResponseDTO)
        assert result.upload_url == upload_url
        mock_file_upload_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_s3_service_error(
        self, use_case, valid_request, mock_s3_service, mock_file_upload_repository
    ):
        mock_s3_service.generate_presigned_upload_url.side_effect = Exception(
            "S3 error"
        )
        mock_file_upload_repository.save = AsyncMock()
        with pytest.raises(
            BusinessRuleViolationError, match="Falha na criação do upload"
        ):
            await use_case.execute(valid_request)

    @pytest.mark.asyncio
    async def test_execute_repository_error(
        self, use_case, valid_request, mock_s3_service, mock_file_upload_repository
    ):
        upload_url = "https://test-bucket.s3.amazonaws.com/presigned-url"
        expires_at = datetime.now(timezone.utc)
        upload_fields = {}
        mock_s3_service.generate_presigned_upload_url.return_value = (
            upload_url,
            expires_at,
            upload_fields,
        )
        mock_file_upload_repository.save = AsyncMock(side_effect=Exception("DB error"))
        with pytest.raises(
            BusinessRuleViolationError, match="Falha na criação do upload"
        ):
            await use_case.execute(valid_request)

    def test_validate_request_empty_filename(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="", file_size=1024000, content_type="application/pdf"
        )
        with pytest.raises(
            BusinessRuleViolationError, match="Nome do arquivo é obrigatório"
        ):
            use_case._validate_request(request)

    def test_validate_request_whitespace_filename(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="   ", file_size=1024000, content_type="application/pdf"
        )
        with pytest.raises(
            BusinessRuleViolationError, match="Nome do arquivo é obrigatório"
        ):
            use_case._validate_request(request)

    def test_validate_request_zero_file_size(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="test.pdf", file_size=0, content_type="application/pdf"
        )
        with pytest.raises(
            BusinessRuleViolationError,
            match="Tamanho do arquivo deve ser maior que zero",
        ):
            use_case._validate_request(request)

    def test_validate_request_negative_file_size(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="test.pdf", file_size=-1000, content_type="application/pdf"
        )
        with pytest.raises(
            BusinessRuleViolationError,
            match="Tamanho do arquivo deve ser maior que zero",
        ):
            use_case._validate_request(request)

    def test_validate_request_file_too_large(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="test.pdf",
            file_size=6 * 1024 * 1024 * 1024,  # 6GB
            content_type="application/pdf",
        )
        with pytest.raises(
            BusinessRuleViolationError, match="Arquivo não pode ser maior que 5GB"
        ):
            use_case._validate_request(request)

    def test_validate_request_unsupported_content_type(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="test.txt", file_size=1024000, content_type="text/plain"
        )
        with pytest.raises(
            BusinessRuleViolationError, match="Tipo de arquivo não suportado"
        ):
            use_case._validate_request(request)

    def test_validate_request_unsupported_extension(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="test.txt", file_size=1024000, content_type="application/pdf"
        )
        with pytest.raises(
            BusinessRuleViolationError, match="Extensão de arquivo não suportada"
        ):
            use_case._validate_request(request)

    def test_validate_request_no_extension(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="testfile", file_size=1024000, content_type="application/pdf"
        )
        with pytest.raises(
            BusinessRuleViolationError, match="Extensão de arquivo não suportada"
        ):
            use_case._validate_request(request)

    def test_validate_request_title_too_long(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="test.pdf",
            file_size=1024000,
            content_type="application/pdf",
            title="a" * 256,
        )
        with pytest.raises(
            BusinessRuleViolationError,
            match="Título não pode ter mais de 255 caracteres",
        ):
            use_case._validate_request(request)

    def test_validate_request_description_too_long(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="test.pdf",
            file_size=1024000,
            content_type="application/pdf",
            description="a" * 1001,
        )
        with pytest.raises(
            BusinessRuleViolationError,
            match="Descrição não pode ter mais de 1000 caracteres",
        ):
            use_case._validate_request(request)

    def test_validate_request_too_many_tags(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="test.pdf",
            file_size=1024000,
            content_type="application/pdf",
            tags=[f"tag{i}" for i in range(11)],
        )
        with pytest.raises(
            BusinessRuleViolationError, match="Máximo de 10 tags permitidas"
        ):
            use_case._validate_request(request)

    def test_validate_request_tag_too_long(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="test.pdf",
            file_size=1024000,
            content_type="application/pdf",
            tags=["a" * 51],
        )
        with pytest.raises(
            BusinessRuleViolationError, match="Tags não podem ter mais de 50 caracteres"
        ):
            use_case._validate_request(request)

    def test_validate_request_valid_pdf(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="document.pdf", file_size=1024000, content_type="application/pdf"
        )
        use_case._validate_request(request)

    def test_validate_request_valid_docx(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="document.docx",
            file_size=1024000,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        use_case._validate_request(request)

    def test_validate_request_valid_doc(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="document.doc",
            file_size=1024000,
            content_type="application/msword",
        )
        use_case._validate_request(request)

    def test_validate_request_case_insensitive_extension(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="document.PDF", file_size=1024000, content_type="application/pdf"
        )
        use_case._validate_request(request)

    def test_validate_request_valid_with_all_optional_fields(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="test.pdf",
            file_size=1024000,
            content_type="application/pdf",
            title="Valid Title",
            description="Valid description",
            tags=["tag1", "tag2", "tag3"],
        )
        use_case._validate_request(request)

    def test_validate_request_empty_tags_list(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="test.pdf",
            file_size=1024000,
            content_type="application/pdf",
            tags=[],
        )
        use_case._validate_request(request)

    def test_validate_request_none_optional_fields(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="test.pdf",
            file_size=1024000,
            content_type="application/pdf",
            title=None,
            description=None,
            tags=None,
        )
        use_case._validate_request(request)

    def test_validate_request_max_valid_title(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="test.pdf",
            file_size=1024000,
            content_type="application/pdf",
            title="a" * 255,
        )
        use_case._validate_request(request)

    def test_validate_request_max_valid_description(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="test.pdf",
            file_size=1024000,
            content_type="application/pdf",
            description="a" * 1000,
        )
        use_case._validate_request(request)

    def test_validate_request_max_valid_tags(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="test.pdf",
            file_size=1024000,
            content_type="application/pdf",
            tags=[f"tag{i}" for i in range(10)],
        )
        use_case._validate_request(request)

    def test_validate_request_max_valid_tag_length(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="test.pdf",
            file_size=1024000,
            content_type="application/pdf",
            tags=["a" * 50],
        )
        use_case._validate_request(request)

    def test_validate_request_max_valid_file_size(self, use_case):
        request = PresignedUploadRequestDTO(
            filename="test.pdf",
            file_size=5 * 1024 * 1024 * 1024,  # Exactly 5GB
            content_type="application/pdf",
        )
        use_case._validate_request(request)
