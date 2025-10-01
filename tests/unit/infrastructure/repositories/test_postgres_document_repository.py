import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.document import Document, DocumentChunk
from domain.exceptions.document_exceptions import DocumentProcessingError
from domain.value_objects.document_metadata import DocumentMetadata
from domain.value_objects.embedding import Embedding
from infrastructure.repositories.postgres_document_repository import (
    PostgresDocumentRepository,
    PostgresDocumentChunkRepository
)
from infrastructure.database.models import DocumentoModel, DocumentoChunkModel
from tests.helpers.mock_factories import MockFactory


class TestPostgresDocumentRepository:
    
    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def repository(self, mock_session):
        return PostgresDocumentRepository(mock_session)
    
    @pytest.fixture
    def sample_document(self):
        return MockFactory.create_document(chunk_count=2)

    def test_init(self, mock_session):
        repo = PostgresDocumentRepository(mock_session)
        assert repo._session == mock_session

    @pytest.mark.asyncio
    async def test_save_new_document_success(self, repository, mock_session, sample_document):
        # Mock para documento não existente
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()
        
        result = await repository.save(sample_document)
        
        assert result == sample_document
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_existing_document_success(self, repository, mock_session, sample_document):
        existing_model = Mock(spec=DocumentoModel)
        existing_model.titulo = "Old Title"
        existing_model.conteudo = "Old Content"
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = existing_model
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()
        
        result = await repository.save(sample_document)
        
        assert result == sample_document
        assert existing_model.titulo == sample_document.title
        assert existing_model.conteudo == sample_document.content
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_document_integrity_error(self, repository, mock_session, sample_document):
        # Mock para documento não existente
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.flush.side_effect = IntegrityError("statement", "params", "orig")
        mock_session.rollback = AsyncMock()
        
        with pytest.raises(DocumentProcessingError):
            await repository.save(sample_document)
        
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_id_found(self, repository, mock_session, sample_document):
        mock_model = Mock(spec=DocumentoModel)
        mock_model.id = sample_document.id
        mock_model.titulo = sample_document.title
        mock_model.conteudo = sample_document.content
        mock_model.caminho_arquivo = sample_document.metadata.source
        mock_model.meta_data = {}
        mock_model.criado_em = sample_document.created_at
        mock_model.atualizado_em = sample_document.updated_at
        
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_model
        
        with patch.object(repository, '_model_to_entity', return_value=sample_document):
            result = await repository.find_by_id(sample_document.id)
        
        assert result == sample_document

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_by_id(uuid4())
        
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_source_found(self, repository, mock_session, sample_document):
        mock_model = Mock(spec=DocumentoModel)
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_model
        
        with patch.object(repository, '_model_to_entity', return_value=sample_document):
            result = await repository.find_by_source("test.pdf")
        
        assert result == sample_document

    @pytest.mark.asyncio
    async def test_find_by_source_not_found(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_by_source("nonexistent.pdf")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_find_all_success(self, repository, mock_session, sample_document):
        mock_model = Mock(spec=DocumentoModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_document):
            result = await repository.find_all()
        
        assert len(result) == 1
        assert result[0] == sample_document

    @pytest.mark.asyncio
    async def test_find_all_with_limit(self, repository, mock_session, sample_document):
        mock_model = Mock(spec=DocumentoModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_document):
            result = await repository.find_all(limit=5, offset=10)
        
        assert len(result) == 1
        assert result[0] == sample_document

    @pytest.mark.asyncio
    async def test_find_all_empty(self, repository, mock_session):
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_all()
        
        assert result == []

    @pytest.mark.asyncio
    async def test_find_by_title_similarity(self, repository, mock_session, sample_document):
        mock_model = Mock(spec=DocumentoModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_document):
            result = await repository.find_by_title_similarity("Test", 0.8)
        
        assert len(result) == 1
        assert result[0] == sample_document

    @pytest.mark.asyncio
    async def test_find_by_content_search(self, repository, mock_session, sample_document):
        mock_model = Mock(spec=DocumentoModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_document):
            result = await repository.find_by_content_search("test content")
        
        assert len(result) == 1
        assert result[0] == sample_document

    @pytest.mark.asyncio
    async def test_update_success(self, repository, mock_session, sample_document):
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        
        result = await repository.update(sample_document)
        
        assert result == sample_document
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, repository, mock_session, sample_document):
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result
        
        with pytest.raises(DocumentProcessingError):
            await repository.update(sample_document)

    @pytest.mark.asyncio
    async def test_update_integrity_error(self, repository, mock_session, sample_document):
        mock_session.execute.side_effect = IntegrityError("statement", "params", "orig")
        mock_session.rollback = AsyncMock()
        
        with pytest.raises(DocumentProcessingError):
            await repository.update(sample_document)
        
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_success(self, repository, mock_session):
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        
        result = await repository.delete(uuid4())
        
        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_session):
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result
        
        result = await repository.delete(uuid4())
        
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result
        
        result = await repository.exists("test.pdf")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result
        
        result = await repository.exists("nonexistent.pdf")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_by_content_hash_true(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result
        
        result = await repository.exists_by_content_hash("test content")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_by_content_hash_false(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result
        
        result = await repository.exists_by_content_hash("unique content")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_count_success(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result
        
        result = await repository.count()
        
        assert result == 5

    @pytest.mark.asyncio
    async def test_find_by_content_hash_found(self, repository, mock_session, sample_document):
        mock_model = Mock(spec=DocumentoModel)
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_model
        
        with patch.object(repository, '_model_to_entity', return_value=sample_document):
            result = await repository.find_by_content_hash("test_hash")
        
        assert result == sample_document

    @pytest.mark.asyncio
    async def test_find_by_content_hash_not_found(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_by_content_hash("nonexistent_hash")
        
        assert result is None

    def test_calculate_file_hash(self, repository):
        content = "test content"
        
        result = repository._calculate_file_hash(content)
        
        assert isinstance(result, str)
        assert len(result) == 64

    def test_metadata_to_dict(self, repository):
        metadata = MockFactory.create_document_metadata()
        
        result = repository._metadata_to_dict(metadata)
        
        assert isinstance(result, dict)
        assert "source" in result
        assert "document_type" in result

    def test_dict_to_metadata(self, repository):
        metadata_dict = {
            "source": "test.pdf",
            "document_type": "pdf",
            "file_size": 1024,
            "page_count": 10,
            "author": "Test Author",
            "title": "Test Title",
            "language": "pt-BR",
            "created_date": datetime.utcnow().isoformat()
        }
        
        result = repository._dict_to_metadata(metadata_dict)
        
        assert isinstance(result, DocumentMetadata)
        assert result.source == "test.pdf"
        assert result.file_type == "pdf"

    def test_model_to_entity(self, repository):
        mock_model = Mock(spec=DocumentoModel)
        mock_model.id = uuid4()
        mock_model.titulo = "Test Title"
        mock_model.conteudo = "Test Content"
        mock_model.caminho_arquivo = "test.pdf"
        mock_model.meta_data = {
            "source": "test.pdf",
            "document_type": "pdf",
            "file_size": 1024,
            "page_count": 10,
            "author": "Test Author",
            "title": "Test Title",
            "language": "pt-BR",
            "created_date": datetime.utcnow().isoformat()
        }
        mock_model.criado_em = datetime.utcnow()
        mock_model.atualizado_em = datetime.utcnow()
        
        result = repository._model_to_entity(mock_model)
        
        assert isinstance(result, Document)
        assert result.id == mock_model.id
        assert result.title == mock_model.titulo
        assert result.content == mock_model.conteudo


class TestPostgresDocumentChunkRepository:
    
    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def repository(self, mock_session):
        return PostgresDocumentChunkRepository(mock_session)
    
    @pytest.fixture
    def sample_chunk(self):
        return MockFactory.create_document_chunk(with_embedding=True)

    def test_init(self, mock_session):
        repo = PostgresDocumentChunkRepository(mock_session)
        assert repo._session == mock_session

    @pytest.mark.asyncio
    async def test_save_chunk_success(self, repository, mock_session, sample_chunk):
        mock_session.flush = AsyncMock()
        
        result = await repository.save_chunk(sample_chunk)
        
        assert result == sample_chunk
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_chunk_integrity_error(self, repository, mock_session, sample_chunk):
        mock_session.flush.side_effect = IntegrityError("statement", "params", "orig")
        mock_session.rollback = AsyncMock()
        
        with pytest.raises(DocumentProcessingError):
            await repository.save_chunk(sample_chunk)
        
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_chunk_by_id_found(self, repository, mock_session, sample_chunk):
        mock_model = Mock(spec=DocumentoChunkModel)
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_model
        
        with patch.object(repository, '_model_to_entity', return_value=sample_chunk):
            result = await repository.find_chunk_by_id(sample_chunk.id)
        
        assert result == sample_chunk

    @pytest.mark.asyncio
    async def test_find_chunk_by_id_not_found(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_chunk_by_id(uuid4())
        
        assert result is None

    @pytest.mark.asyncio
    async def test_find_chunks_by_document_id_success(self, repository, mock_session, sample_chunk):
        mock_model = Mock(spec=DocumentoChunkModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_chunk):
            result = await repository.find_chunks_by_document_id(uuid4())
        
        assert len(result) == 1
        assert result[0] == sample_chunk

    @pytest.mark.asyncio
    async def test_find_chunks_by_document_id_empty(self, repository, mock_session):
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_chunks_by_document_id(uuid4())
        
        assert result == []

    @pytest.mark.asyncio
    async def test_delete_chunks_by_document_id_success(self, repository, mock_session):
        mock_result = Mock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result
        
        result = await repository.delete_chunks_by_document_id(uuid4())
        
        assert result == 3
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_chunk_embedding_success(self, repository, sample_chunk):
        embedding = MockFactory.create_embedding()
        
        result = await repository.update_chunk_embedding(sample_chunk.id, embedding)
        
        assert result is True

    def test_model_to_entity(self, repository):
        mock_model = Mock(spec=DocumentoChunkModel)
        mock_model.id = uuid4()
        mock_model.documento_id = uuid4()
        mock_model.conteudo = "Test chunk content"
        mock_model.indice_chunk = 0
        mock_model.start_char = 0
        mock_model.end_char = 100
        mock_model.criado_em = datetime.utcnow()
        
        result = repository._model_to_entity(mock_model)
        
        assert isinstance(result, DocumentChunk)
        assert result.id == mock_model.id
        assert result.document_id == mock_model.documento_id
        assert result.content == mock_model.conteudo
        assert result.chunk_index == mock_model.indice_chunk