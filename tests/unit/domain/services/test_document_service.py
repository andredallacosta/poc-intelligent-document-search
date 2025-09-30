import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from domain.services.document_service import DocumentService
from domain.entities.document import Document, DocumentChunk
from domain.exceptions.document_exceptions import (
    DocumentAlreadyExistsError,
    DocumentNotFoundError,
    InvalidDocumentError
)
from domain.repositories.document_repository import DocumentRepository

class TestDocumentService:
    
    @pytest.fixture
    def mock_document_repository(self):
        return Mock(spec=DocumentRepository)
    
    @pytest.fixture
    def document_service(self, mock_document_repository):
        return DocumentService(document_repository=mock_document_repository)
    
    @pytest.fixture
    def sample_document(self, sample_document_metadata):
        return Document(
            id=uuid4(),
            title="Test Document",
            content="This is test content for the document",
            file_path="/test/document.pdf",
            metadata=sample_document_metadata,
            chunks=[]
        )
    
    @pytest.mark.asyncio
    async def test_create_document_success(
        self, 
        document_service, 
        mock_document_repository, 
        sample_document_metadata
    ):
        mock_document_repository.exists = AsyncMock(return_value=False)
        mock_document_repository.save = AsyncMock(return_value=Mock())
        
        result = await document_service.create_document(
            title="Test Document",
            content="This is test content",
            file_path="/test/doc.pdf",
            metadata=sample_document_metadata
        )
        
        mock_document_repository.exists.assert_called_once_with(sample_document_metadata.source)
        mock_document_repository.save.assert_called_once()
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_create_document_empty_title_raises_error(
        self, 
        document_service, 
        sample_document_metadata
    ):
        with pytest.raises(InvalidDocumentError, match="Document title cannot be empty"):
            await document_service.create_document(
                title="   ",
                content="Valid content",
                file_path="/test/doc.pdf",
                metadata=sample_document_metadata
            )
    
    @pytest.mark.asyncio
    async def test_create_document_empty_content_raises_error(
        self, 
        document_service, 
        sample_document_metadata
    ):
        with pytest.raises(InvalidDocumentError, match="Document content cannot be empty"):
            await document_service.create_document(
                title="Valid Title",
                content="   ",
                file_path="/test/doc.pdf",
                metadata=sample_document_metadata
            )
    
    @pytest.mark.asyncio
    async def test_create_document_already_exists_raises_error(
        self, 
        document_service, 
        mock_document_repository, 
        sample_document_metadata
    ):
        mock_document_repository.exists = AsyncMock(return_value=True)
        
        with pytest.raises(DocumentAlreadyExistsError):
            await document_service.create_document(
                title="Test Document",
                content="Valid content",
                file_path="/test/doc.pdf",
                metadata=sample_document_metadata
            )
    
    @pytest.mark.asyncio
    async def test_get_document_by_id_success(
        self, 
        document_service, 
        mock_document_repository, 
        sample_document
    ):
        document_id = sample_document.id
        mock_document_repository.find_by_id = AsyncMock(return_value=sample_document)
        
        result = await document_service.get_document_by_id(document_id)
        
        mock_document_repository.find_by_id.assert_called_once_with(document_id)
        assert result == sample_document
    
    @pytest.mark.asyncio
    async def test_get_document_by_id_not_found_raises_error(
        self, 
        document_service, 
        mock_document_repository
    ):
        document_id = uuid4()
        mock_document_repository.find_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(DocumentNotFoundError):
            await document_service.get_document_by_id(document_id)
    
    @pytest.mark.asyncio
    async def test_get_document_by_source_success(
        self, 
        document_service, 
        mock_document_repository, 
        sample_document
    ):
        source = "test_document.pdf"
        mock_document_repository.find_by_source = AsyncMock(return_value=sample_document)
        
        result = await document_service.get_document_by_source(source)
        
        mock_document_repository.find_by_source.assert_called_once_with(source)
        assert result == sample_document
    
    @pytest.mark.asyncio
    async def test_get_document_by_source_not_found(
        self, 
        document_service, 
        mock_document_repository
    ):
        source = "nonexistent.pdf"
        mock_document_repository.find_by_source = AsyncMock(return_value=None)
        
        result = await document_service.get_document_by_source(source)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_list_documents(
        self, 
        document_service, 
        mock_document_repository, 
        sample_document
    ):
        documents = [sample_document]
        mock_document_repository.find_all = AsyncMock(return_value=documents)
        
        result = await document_service.list_documents(limit=10, offset=0)
        
        mock_document_repository.find_all.assert_called_once_with(limit=10, offset=0)
        assert result == documents
    
    @pytest.mark.asyncio
    async def test_delete_document_success(
        self, 
        document_service, 
        mock_document_repository, 
        sample_document
    ):
        document_id = sample_document.id
        mock_document_repository.find_by_id = AsyncMock(return_value=sample_document)
        mock_document_repository.delete = AsyncMock(return_value=True)
        
        result = await document_service.delete_document(document_id)
        
        mock_document_repository.find_by_id.assert_called_once_with(document_id)
        mock_document_repository.delete.assert_called_once_with(document_id)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_document_not_found_raises_error(
        self, 
        document_service, 
        mock_document_repository
    ):
        document_id = uuid4()
        mock_document_repository.find_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(DocumentNotFoundError):
            await document_service.delete_document(document_id)
    
    @pytest.mark.asyncio
    async def test_add_chunks_to_document_success(
        self, 
        document_service, 
        mock_document_repository, 
        sample_document,
        mock_data_factory
    ):
        document_id = sample_document.id
        chunks = [
            mock_data_factory.create_document_chunk(content="Chunk 1", chunk_index=0),
            mock_data_factory.create_document_chunk(content="Chunk 2", chunk_index=1)
        ]
        
        mock_document_repository.find_by_id = AsyncMock(return_value=sample_document)
        mock_document_repository.save = AsyncMock(return_value=sample_document)
        
        result = await document_service.add_chunks_to_document(document_id, chunks)
        
        mock_document_repository.save.assert_called_once()
        assert result == sample_document
        
        for chunk in chunks:
            assert chunk.document_id == document_id
    
    def test_validate_document_content_valid(self, document_service):
        assert document_service.validate_document_content("This is valid content with enough text") is True
    
    def test_validate_document_content_empty(self, document_service):
        assert document_service.validate_document_content("") is False
        assert document_service.validate_document_content("   ") is False
        assert document_service.validate_document_content(None) is False
    
    def test_validate_document_content_too_short(self, document_service):
        assert document_service.validate_document_content("short") is False
        assert document_service.validate_document_content("123456789") is False
    
    def test_validate_document_content_minimum_length(self, document_service):
        assert document_service.validate_document_content("1234567890") is True
    
    def test_calculate_document_stats(self, document_service, sample_document):
        chunk1 = DocumentChunk(
            id=uuid4(),
            document_id=sample_document.id,
            content="First chunk content",
            original_content="First chunk content",
            chunk_index=0,
            start_char=0,
            end_char=19
        )
        chunk2 = DocumentChunk(
            id=uuid4(),
            document_id=sample_document.id,
            content="Second chunk content",
            original_content="Second chunk content",
            chunk_index=1,
            start_char=20,
            end_char=40
        )
        
        sample_document.add_chunk(chunk1)
        sample_document.add_chunk(chunk2)
        
        stats = document_service.calculate_document_stats(sample_document)
        
        assert "word_count" in stats
        assert "chunk_count" in stats
        assert "file_size_mb" in stats
        assert "average_chunk_size" in stats
        
        assert stats["chunk_count"] == 2
        assert stats["word_count"] == sample_document.word_count
        assert stats["file_size_mb"] == sample_document.metadata.size_mb
        assert isinstance(stats["average_chunk_size"], int)
    
    def test_calculate_document_stats_no_chunks(self, document_service, sample_document):
        stats = document_service.calculate_document_stats(sample_document)
        
        assert stats["chunk_count"] == 0
        assert stats["average_chunk_size"] == len(sample_document.content)
