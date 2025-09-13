import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4
from typing import List

from domain.services.search_service import SearchService
from domain.entities.message import DocumentReference
from domain.value_objects.embedding import Embedding
from domain.repositories.vector_repository import VectorRepository, SearchResult


class TestSearchService:
    
    @pytest.fixture
    def mock_vector_repository(self):
        return Mock(spec=VectorRepository)
    
    @pytest.fixture
    def search_service(self, mock_vector_repository):
        return SearchService(vector_repository=mock_vector_repository)
    
    @pytest.fixture
    def sample_search_results(self, mock_data_factory):
        return mock_data_factory.create_search_results(3)
    
    @pytest.mark.asyncio
    async def test_search_similar_content_success(self, search_service, mock_vector_repository, sample_embedding, sample_search_results):
        # Arrange
        mock_vector_repository.search_similar_chunks = AsyncMock(return_value=sample_search_results)
        
        # Act
        results = await search_service.search_similar_content(
            query_embedding=sample_embedding,
            n_results=3,
            similarity_threshold=0.7
        )
        
        # Assert
        assert len(results) == 3
        mock_vector_repository.search_similar_chunks.assert_called_once_with(
            query_embedding=sample_embedding,
            n_results=3,
            similarity_threshold=0.7,
            metadata_filter=None
        )
    
    @pytest.mark.asyncio
    async def test_search_similar_content_with_metadata_filter(self, search_service, mock_vector_repository, sample_embedding):
        # Arrange
        metadata_filter = {"document_type": "pdf"}
        mock_vector_repository.search_similar_chunks = AsyncMock(return_value=[])
        
        # Act
        await search_service.search_similar_content(
            query_embedding=sample_embedding,
            n_results=5,
            similarity_threshold=0.8,
            metadata_filter=metadata_filter
        )
        
        # Assert
        mock_vector_repository.search_similar_chunks.assert_called_once_with(
            query_embedding=sample_embedding,
            n_results=5,
            similarity_threshold=0.8,
            metadata_filter=metadata_filter
        )
    
    @pytest.mark.asyncio
    async def test_search_similar_content_empty_results(self, search_service, mock_vector_repository, sample_embedding):
        # Arrange
        mock_vector_repository.search_similar_chunks = AsyncMock(return_value=[])
        
        # Act
        results = await search_service.search_similar_content(
            query_embedding=sample_embedding,
            n_results=3
        )
        
        # Assert
        assert results == []
    
    def test_convert_results_to_references(self, search_service, sample_search_results):
        # Act
        references = search_service.convert_results_to_references(sample_search_results)
        
        # Assert
        assert len(references) == 3
        
        for i, reference in enumerate(references):
            assert isinstance(reference, DocumentReference)
            assert reference.document_id == sample_search_results[i].chunk.document_id
            assert reference.chunk_id == sample_search_results[i].chunk.id
            assert reference.similarity_score == sample_search_results[i].similarity_score
    
    def test_convert_empty_results_to_references(self, search_service):
        # Act
        references = search_service.convert_results_to_references([])
        
        # Assert
        assert references == []
    
    def test_calculate_relevance_score_basic(self, search_service):
        # Act
        score = search_service.calculate_relevance_score(0.8)
        
        # Assert
        assert score == 0.8
    
    def test_calculate_relevance_score_with_factors(self, search_service):
        # Act
        score = search_service.calculate_relevance_score(
            similarity_score=0.8,
            document_popularity=1.2,
            recency_factor=0.9
        )
        
        # Assert
        expected = 0.8 * 1.2 * 0.9
        assert score == pytest.approx(expected, abs=1e-6)
    
    @pytest.mark.asyncio
    async def test_search_by_document_type(self, search_service, mock_vector_repository, sample_embedding):
        # Arrange
        mock_vector_repository.search_similar_chunks = AsyncMock(return_value=[])
        
        # Act
        await search_service.search_by_document_type(
            query_embedding=sample_embedding,
            document_type="pdf",
            n_results=3
        )
        
        # Assert
        mock_vector_repository.search_similar_chunks.assert_called_once()
        call_args = mock_vector_repository.search_similar_chunks.call_args
        assert call_args[1]["metadata_filter"] == {"file_type": "pdf"}
    
    @pytest.mark.asyncio
    async def test_search_by_source(self, search_service, mock_vector_repository, sample_embedding):
        # Arrange
        mock_vector_repository.search_similar_chunks = AsyncMock(return_value=[])
        
        # Act
        await search_service.search_by_source(
            query_embedding=sample_embedding,
            source="test_doc.pdf",
            n_results=5
        )
        
        # Assert
        mock_vector_repository.search_similar_chunks.assert_called_once()
        call_args = mock_vector_repository.search_similar_chunks.call_args
        assert call_args[1]["metadata_filter"] == {"source": "test_doc.pdf"}
    
    @pytest.mark.asyncio
    async def test_search_with_custom_parameters(self, search_service, mock_vector_repository, sample_embedding):
        # Arrange
        mock_vector_repository.search_similar_chunks = AsyncMock(return_value=[])
        
        # Act
        await search_service.search_similar_content(
            query_embedding=sample_embedding,
            n_results=10,
            similarity_threshold=0.9,
            metadata_filter={"language": "pt-BR"}
        )
        
        # Assert
        mock_vector_repository.search_similar_chunks.assert_called_once_with(
            query_embedding=sample_embedding,
            n_results=10,
            similarity_threshold=0.9,
            metadata_filter={"language": "pt-BR"}
        )
