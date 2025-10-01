import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
import tempfile
from pathlib import Path

from domain.services.document_processor import DocumentProcessor
from domain.entities.document import Document, DocumentChunk
from domain.entities.document_processing_job import DocumentProcessingJob
from domain.entities.file_upload import FileUpload
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.content_hash import ContentHash
from domain.value_objects.document_metadata import DocumentMetadata
from domain.value_objects.processing_status import ProcessingStatus
from domain.value_objects.s3_key import S3Key


class TestDocumentProcessor:
    
    @pytest.fixture
    def mock_document_service(self):
        return Mock()
    
    @pytest.fixture
    def mock_vector_repository(self):
        return Mock()
    
    @pytest.fixture
    def mock_text_chunker(self):
        return Mock()
    
    @pytest.fixture
    def mock_openai_client(self):
        return Mock()
    
    @pytest.fixture
    def mock_s3_service(self):
        return Mock()
    
    @pytest.fixture
    def mock_document_repository(self):
        return Mock()
    
    @pytest.fixture
    def document_processor(
        self,
        mock_document_service,
        mock_vector_repository,
        mock_text_chunker,
        mock_openai_client,
        mock_s3_service,
        mock_document_repository
    ):
        return DocumentProcessor(
            document_service=mock_document_service,
            vector_repository=mock_vector_repository,
            text_chunker=mock_text_chunker,
            openai_client=mock_openai_client,
            s3_service=mock_s3_service,
            document_repository=mock_document_repository
        )
    
    @pytest.fixture
    def sample_file_upload(self):
        return FileUpload(
            id=uuid4(),
            filename="test_document.pdf",
            content_type="application/pdf",
            file_size=1024,
            s3_key=S3Key(bucket="test-bucket", key="uploads/test_document.pdf")
        )
    
    @pytest.fixture
    def sample_processing_job(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        return DocumentProcessingJob(
            id=uuid4(),
            upload_id=uuid4(),
            status=ProcessingStatus.UPLOADED,
            started_at=now,
            completed_at=None
        )
    
    @pytest.fixture
    def sample_document(self):
        metadata = DocumentMetadata(
            source="test_document.pdf",
            file_size=1024,
            file_type="application/pdf"
        )
        return Document(
            id=uuid4(),
            title="Test Document",
            content="This is test content for the document",
            file_path="/test/document.pdf",
            metadata=metadata,
            chunks=[]
        )
    
    @pytest.fixture
    def sample_chunks(self, sample_document):
        return [
            DocumentChunk(
                id=uuid4(),
                document_id=sample_document.id,
                content="First chunk content",
                original_content="First chunk content",
                chunk_index=0,
                start_char=0,
                end_char=19
            ),
            DocumentChunk(
                id=uuid4(),
                document_id=sample_document.id,
                content="Second chunk content",
                original_content="Second chunk content",
                chunk_index=1,
                start_char=20,
                end_char=40
            )
        ]

    @pytest.mark.asyncio
    async def test_process_uploaded_document_success(
        self,
        document_processor,
        sample_file_upload,
        sample_processing_job,
        sample_document,
        sample_chunks,
        mock_s3_service,
        mock_document_repository,
        mock_document_service,
        mock_text_chunker,
        mock_openai_client,
        mock_vector_repository
    ):
        text_content = "This is the extracted text content from the document"
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        
        mock_s3_service.download_file = AsyncMock(return_value=True)
        mock_document_repository.find_by_content_hash = AsyncMock(return_value=None)
        mock_document_repository.find_by_source = AsyncMock(return_value=None)
        mock_document_service.create_document = AsyncMock(return_value=sample_document)
        mock_document_service.add_chunks_to_document = AsyncMock(return_value=sample_document)
        mock_document_service.get_document_chunks = AsyncMock(return_value=sample_chunks)
        mock_text_chunker.chunk_document_content = Mock(return_value=sample_chunks)
        mock_openai_client.generate_embeddings_batch = AsyncMock(return_value=embeddings)
        mock_vector_repository.add_chunk_embedding = AsyncMock()
        mock_s3_service.delete_file = AsyncMock(return_value=True)
        
        with patch.object(document_processor, '_download_and_extract_text', return_value=text_content):
            result = await document_processor.process_uploaded_document(sample_file_upload, sample_processing_job)
        
        assert result == sample_document
        assert sample_processing_job.status == ProcessingStatus.COMPLETED
        mock_document_service.create_document.assert_called_once()
        mock_document_service.add_chunks_to_document.assert_called_once()
        mock_openai_client.generate_embeddings_batch.assert_called_once()
        mock_s3_service.delete_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_uploaded_document_duplicate_by_content(
        self,
        document_processor,
        sample_file_upload,
        sample_processing_job,
        sample_document,
        mock_s3_service,
        mock_document_repository
    ):
        text_content = "This is the extracted text content from the document"
        
        mock_s3_service.download_file = AsyncMock(return_value=True)
        mock_document_repository.find_by_content_hash = AsyncMock(return_value=sample_document)
        mock_s3_service.delete_file = AsyncMock(return_value=True)
        
        with patch.object(document_processor, '_download_and_extract_text', return_value=text_content), \
             patch.object(sample_processing_job, 'mark_as_duplicate') as mock_mark_duplicate:
            result = await document_processor.process_uploaded_document(sample_file_upload, sample_processing_job)
        
        assert result == sample_document
        mock_mark_duplicate.assert_called_once_with(sample_document.id)
        mock_s3_service.delete_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_uploaded_document_duplicate_by_source(
        self,
        document_processor,
        sample_file_upload,
        sample_processing_job,
        sample_document,
        mock_s3_service,
        mock_document_repository
    ):
        text_content = "This is the extracted text content from the document"
        
        mock_s3_service.download_file = AsyncMock(return_value=True)
        mock_document_repository.find_by_content_hash = AsyncMock(return_value=None)
        mock_document_repository.find_by_source = AsyncMock(return_value=sample_document)
        mock_s3_service.delete_file = AsyncMock(return_value=True)
        
        with patch.object(document_processor, '_download_and_extract_text', return_value=text_content), \
             patch.object(sample_processing_job, 'mark_as_duplicate') as mock_mark_duplicate:
            result = await document_processor.process_uploaded_document(sample_file_upload, sample_processing_job)
        
        assert result == sample_document
        mock_mark_duplicate.assert_called_once_with(sample_document.id)
        mock_s3_service.delete_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_uploaded_document_extraction_failure(
        self,
        document_processor,
        sample_file_upload,
        sample_processing_job
    ):
        with patch.object(document_processor, '_download_and_extract_text', side_effect=BusinessRuleViolationError("Extraction failed")):
            with pytest.raises(BusinessRuleViolationError, match="Falha no processamento"):
                await document_processor.process_uploaded_document(sample_file_upload, sample_processing_job)
        
        assert sample_processing_job.status == ProcessingStatus.FAILED
        assert "Extraction failed" in sample_processing_job.error_message

    @pytest.mark.asyncio
    async def test_download_and_extract_text_pdf_success(
        self,
        document_processor,
        sample_file_upload,
        sample_processing_job,
        mock_s3_service
    ):
        sample_file_upload.content_type = "application/pdf"
        mock_s3_service.download_file = AsyncMock(return_value=True)
        
        with patch.object(document_processor, '_extract_text_from_pdf', return_value="Extracted PDF text"):
            result = await document_processor._download_and_extract_text(sample_file_upload, sample_processing_job)
        
        assert result == "Extracted PDF text"
        mock_s3_service.download_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_and_extract_text_docx_success(
        self,
        document_processor,
        sample_file_upload,
        sample_processing_job,
        mock_s3_service
    ):
        sample_file_upload.content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        mock_s3_service.download_file = AsyncMock(return_value=True)
        
        with patch.object(document_processor, '_extract_text_from_docx', return_value="Extracted DOCX text"):
            result = await document_processor._download_and_extract_text(sample_file_upload, sample_processing_job)
        
        assert result == "Extracted DOCX text"

    @pytest.mark.asyncio
    async def test_download_and_extract_text_doc_success(
        self,
        document_processor,
        sample_file_upload,
        sample_processing_job,
        mock_s3_service
    ):
        sample_file_upload.content_type = "application/msword"
        mock_s3_service.download_file = AsyncMock(return_value=True)
        
        with patch.object(document_processor, '_extract_text_from_doc', return_value="Extracted DOC text"):
            result = await document_processor._download_and_extract_text(sample_file_upload, sample_processing_job)
        
        assert result == "Extracted DOC text"

    @pytest.mark.asyncio
    async def test_download_and_extract_text_unsupported_format(
        self,
        document_processor,
        sample_file_upload,
        sample_processing_job,
        mock_s3_service
    ):
        sample_file_upload.content_type = "text/plain"
        mock_s3_service.download_file = AsyncMock(return_value=True)
        
        with pytest.raises(BusinessRuleViolationError, match="Tipo de arquivo não suportado"):
            await document_processor._download_and_extract_text(sample_file_upload, sample_processing_job)

    @pytest.mark.asyncio
    async def test_download_and_extract_text_s3_download_failure(
        self,
        document_processor,
        sample_file_upload,
        sample_processing_job,
        mock_s3_service
    ):
        mock_s3_service.download_file = AsyncMock(return_value=False)
        
        with pytest.raises(BusinessRuleViolationError, match="Falha no download do S3"):
            await document_processor._download_and_extract_text(sample_file_upload, sample_processing_job)

    @pytest.mark.asyncio
    async def test_download_and_extract_text_insufficient_content(
        self,
        document_processor,
        sample_file_upload,
        sample_processing_job,
        mock_s3_service
    ):
        sample_file_upload.content_type = "application/pdf"
        mock_s3_service.download_file = AsyncMock(return_value=True)
        
        with patch.object(document_processor, '_extract_text_from_pdf', return_value="short"):
            with pytest.raises(BusinessRuleViolationError, match="Documento não contém texto suficiente"):
                await document_processor._download_and_extract_text(sample_file_upload, sample_processing_job)

    @pytest.mark.asyncio
    async def test_download_and_extract_text_no_s3_key(
        self,
        document_processor,
        sample_file_upload,
        sample_processing_job
    ):
        sample_file_upload.s3_key = None
        
        with pytest.raises(BusinessRuleViolationError, match="S3 key não definida para o upload"):
            await document_processor._download_and_extract_text(sample_file_upload, sample_processing_job)

    @pytest.mark.asyncio
    async def test_extract_text_from_pdf_success(self, document_processor):
        mock_documents = [Mock(page_content="Page 1 content"), Mock(page_content="Page 2 content")]
        
        with patch('langchain_community.document_loaders.PDFPlumberLoader') as mock_loader_class:
            mock_loader = Mock()
            mock_loader.load.return_value = mock_documents
            mock_loader_class.return_value = mock_loader
            
            result = await document_processor._extract_text_from_pdf("/fake/path.pdf")
        
        assert result == "Page 1 content\n\nPage 2 content"

    @pytest.mark.asyncio
    async def test_extract_text_from_pdf_failure(self, document_processor):
        with patch('langchain_community.document_loaders.PDFPlumberLoader', side_effect=Exception("PDF error")):
            with pytest.raises(BusinessRuleViolationError, match="Falha na extração de texto PDF"):
                await document_processor._extract_text_from_pdf("/fake/path.pdf")

    @pytest.mark.asyncio
    async def test_extract_text_from_docx_success(self, document_processor):
        mock_paragraph1 = Mock()
        mock_paragraph1.text = "Paragraph 1"
        mock_paragraph2 = Mock()
        mock_paragraph2.text = "Paragraph 2"
        
        with patch('docx.Document') as mock_docx_class:
            mock_doc = Mock()
            mock_doc.paragraphs = [mock_paragraph1, mock_paragraph2]
            mock_docx_class.return_value = mock_doc
            
            result = await document_processor._extract_text_from_docx("/fake/path.docx")
        
        assert result == "Paragraph 1\n\nParagraph 2"

    @pytest.mark.asyncio
    async def test_extract_text_from_docx_failure(self, document_processor):
        with patch('docx.Document', side_effect=Exception("DOCX error")):
            with pytest.raises(BusinessRuleViolationError, match="Falha na extração de texto DOCX"):
                await document_processor._extract_text_from_docx("/fake/path.docx")

    @pytest.mark.asyncio
    async def test_extract_text_from_doc_success(self, document_processor):
        with patch('docx2txt.process', return_value="DOC text content"):
            result = await document_processor._extract_text_from_doc("/fake/path.doc")
        
        assert result == "DOC text content"

    @pytest.mark.asyncio
    async def test_extract_text_from_doc_failure(self, document_processor):
        with patch('docx2txt.process', side_effect=Exception("DOC error")):
            with pytest.raises(BusinessRuleViolationError, match="Falha na extração de texto DOC"):
                await document_processor._extract_text_from_doc("/fake/path.doc")

    @pytest.mark.asyncio
    async def test_check_for_duplicate_no_duplicates(
        self,
        document_processor,
        sample_processing_job,
        sample_file_upload,
        mock_document_repository
    ):
        text_content = "This is unique content"
        mock_document_repository.find_by_content_hash = AsyncMock(return_value=None)
        mock_document_repository.find_by_source = AsyncMock(return_value=None)
        
        result = await document_processor._check_for_duplicate(text_content, sample_processing_job, sample_file_upload)
        
        assert result is None
        assert sample_processing_job.content_hash is not None

    @pytest.mark.asyncio
    async def test_check_for_duplicate_exception_handling(
        self,
        document_processor,
        sample_processing_job,
        sample_file_upload,
        mock_document_repository
    ):
        text_content = "This is content"
        mock_document_repository.find_by_content_hash = AsyncMock(side_effect=Exception("DB error"))
        
        result = await document_processor._check_for_duplicate(text_content, sample_processing_job, sample_file_upload)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_create_document_with_chunks_success(
        self,
        document_processor,
        sample_file_upload,
        sample_processing_job,
        sample_document,
        sample_chunks,
        mock_document_service,
        mock_text_chunker
    ):
        text_content = "This is the document content"
        mock_document_service.create_document = AsyncMock(return_value=sample_document)
        mock_document_service.add_chunks_to_document = AsyncMock(return_value=sample_document)
        mock_text_chunker.chunk_document_content = Mock(return_value=sample_chunks)
        
        result = await document_processor._create_document_with_chunks(
            sample_file_upload, text_content, sample_processing_job
        )
        
        assert result == sample_document
        mock_document_service.create_document.assert_called_once()
        mock_document_service.add_chunks_to_document.assert_called_once()
        mock_text_chunker.chunk_document_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_document_with_chunks_failure(
        self,
        document_processor,
        sample_file_upload,
        sample_processing_job,
        mock_document_service
    ):
        text_content = "This is the document content"
        mock_document_service.create_document = AsyncMock(side_effect=Exception("Creation failed"))
        
        with pytest.raises(BusinessRuleViolationError, match="Falha na criação do documento"):
            await document_processor._create_document_with_chunks(
                sample_file_upload, text_content, sample_processing_job
            )

    @pytest.mark.asyncio
    async def test_generate_and_save_embeddings_success(
        self,
        document_processor,
        sample_document,
        sample_processing_job,
        sample_chunks,
        mock_document_service,
        mock_openai_client,
        mock_vector_repository
    ):
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_document_service.get_document_chunks = AsyncMock(return_value=sample_chunks)
        mock_openai_client.generate_embeddings_batch = AsyncMock(return_value=embeddings)
        mock_vector_repository.add_chunk_embedding = AsyncMock()
        
        await document_processor._generate_and_save_embeddings(sample_document, sample_processing_job)
        
        mock_openai_client.generate_embeddings_batch.assert_called_once()
        assert mock_vector_repository.add_chunk_embedding.call_count == len(sample_chunks)

    @pytest.mark.asyncio
    async def test_generate_and_save_embeddings_no_chunks(
        self,
        document_processor,
        sample_document,
        sample_processing_job,
        mock_document_service
    ):
        mock_document_service.get_document_chunks = AsyncMock(return_value=[])
        
        with pytest.raises(BusinessRuleViolationError, match="Nenhum chunk encontrado para o documento"):
            await document_processor._generate_and_save_embeddings(sample_document, sample_processing_job)

    @pytest.mark.asyncio
    async def test_generate_and_save_embeddings_failure(
        self,
        document_processor,
        sample_document,
        sample_processing_job,
        sample_chunks,
        mock_document_service,
        mock_openai_client
    ):
        mock_document_service.get_document_chunks = AsyncMock(return_value=sample_chunks)
        mock_openai_client.generate_embeddings_batch = AsyncMock(side_effect=Exception("OpenAI error"))
        
        with pytest.raises(BusinessRuleViolationError, match="Falha na geração de embeddings"):
            await document_processor._generate_and_save_embeddings(sample_document, sample_processing_job)

    @pytest.mark.asyncio
    async def test_generate_and_save_embeddings_large_batch(
        self,
        document_processor,
        sample_document,
        sample_processing_job,
        mock_document_service,
        mock_openai_client,
        mock_vector_repository
    ):
        large_chunks = []
        for i in range(45):
            chunk = DocumentChunk(
                id=uuid4(),
                document_id=sample_document.id,
                content=f"Chunk {i} content",
                original_content=f"Chunk {i} content",
                chunk_index=i,
                start_char=i*20,
                end_char=(i+1)*20
            )
            large_chunks.append(chunk)
        
        embeddings_batch1 = [[0.1, 0.2, 0.3]] * 20
        embeddings_batch2 = [[0.4, 0.5, 0.6]] * 20
        embeddings_batch3 = [[0.7, 0.8, 0.9]] * 5
        
        mock_document_service.get_document_chunks = AsyncMock(return_value=large_chunks)
        mock_openai_client.generate_embeddings_batch = AsyncMock(side_effect=[
            embeddings_batch1, embeddings_batch2, embeddings_batch3
        ])
        mock_vector_repository.add_chunk_embedding = AsyncMock()
        
        await document_processor._generate_and_save_embeddings(sample_document, sample_processing_job)
        
        assert mock_openai_client.generate_embeddings_batch.call_count == 3
        assert mock_vector_repository.add_chunk_embedding.call_count == 45

    @pytest.mark.asyncio
    async def test_cleanup_s3_file_success(
        self,
        document_processor,
        sample_file_upload,
        mock_s3_service
    ):
        mock_s3_service.delete_file = AsyncMock(return_value=True)
        
        await document_processor._cleanup_s3_file(sample_file_upload)
        
        mock_s3_service.delete_file.assert_called_once_with(sample_file_upload.s3_key)

    @pytest.mark.asyncio
    async def test_cleanup_s3_file_no_s3_key(
        self,
        document_processor,
        sample_file_upload,
        mock_s3_service
    ):
        sample_file_upload.s3_key = None
        
        await document_processor._cleanup_s3_file(sample_file_upload)
        
        mock_s3_service.delete_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_s3_file_failure(
        self,
        document_processor,
        sample_file_upload,
        mock_s3_service
    ):
        mock_s3_service.delete_file = AsyncMock(return_value=False)
        
        await document_processor._cleanup_s3_file(sample_file_upload)
        
        mock_s3_service.delete_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_s3_file_exception(
        self,
        document_processor,
        sample_file_upload,
        mock_s3_service
    ):
        mock_s3_service.delete_file = AsyncMock(side_effect=Exception("S3 error"))
        
        await document_processor._cleanup_s3_file(sample_file_upload)
        
        mock_s3_service.delete_file.assert_called_once()
