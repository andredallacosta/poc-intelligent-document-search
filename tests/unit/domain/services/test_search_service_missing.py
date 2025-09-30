import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from domain.services.search_service import SearchService
from domain.repositories.vector_repository import VectorRepository, SearchResult
from domain.entities.document import DocumentChunk
from domain.value_objects.embedding import Embedding
from domain.entities.message import DocumentReference

class TestSearchServiceMissingCoverage:
    
    @pytest.fixture
    def mock_vector_repository(self):
        return Mock(spec=VectorRepository)
    
    @pytest.fixture
    def search_service(self, mock_vector_repository):
        return SearchService(mock_vector_repository)
    
    @pytest.fixture
    def sample_search_results(self):
        chunk1 = DocumentChunk(
            id=uuid4(),
            document_id=uuid4(),
            content="First chunk content",
            original_content="First chunk content",
            chunk_index=0,
            start_char=0,
            end_char=20,
            embedding=Embedding.from_openai([0.1, 0.2, 0.3])
        )
        
        chunk2 = DocumentChunk(
            id=uuid4(),
            document_id=uuid4(),
            content="Second chunk content",
            original_content="Second chunk content",
            chunk_index=1,
            start_char=20,
            end_char=40,
            embedding=Embedding.from_openai([0.4, 0.5, 0.6])
        )
        
        return [
            SearchResult(
                chunk=chunk1,
                similarity_score=0.9,
                distance=0.1,
                metadata={"source": "doc1.pdf", "page": 1}
            ),
            SearchResult(
                chunk=chunk2,
                similarity_score=0.8,
                distance=0.2,
                metadata={"source": "doc2.pdf", "page": 2}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_search_similar_content_with_threshold_filtering(self, search_service, mock_vector_repository, sample_search_results):
        query_embedding = Embedding.from_openai([0.1, 0.2, 0.3])
        mock_vector_repository.search_similar_chunks.return_value = sample_search_results
        
        results = await search_service.search_similar_content(
            query="threshold filtering test",
            query_embedding=query_embedding, 
            n_results=5, 
            similarity_threshold=0.85
        )
        
        assert len(results) == 1
        assert results[0].similarity_score == 0.9
        mock_vector_repository.search_similar_chunks.assert_called_once_with(
            query_embedding=query_embedding,
            n_results=5,
            similarity_threshold=0.85,
            metadata_filter=None
        )
    
    def test_convert_results_to_references_with_metadata(self, search_service, sample_search_results):
        references = search_service.convert_results_to_references(sample_search_results)
        
        assert len(references) == 2
        
        ref1 = references[0]
        assert isinstance(ref1, DocumentReference)
        assert ref1.document_id == sample_search_results[0].chunk.document_id
        assert ref1.chunk_id == sample_search_results[0].chunk.id
        assert ref1.source == "doc1.pdf"
        assert ref1.page == 1
        assert ref1.similarity_score == 0.9
        assert ref1.excerpt == "First chunk content"
        
        ref2 = references[1]
        assert ref2.source == "doc2.pdf"
        assert ref2.page == 2
        assert ref2.similarity_score == 0.8
        assert ref2.excerpt == "Second chunk content"
    
    def test_convert_results_to_references_missing_metadata(self, search_service):
        chunk = DocumentChunk(
            id=uuid4(),
            document_id=uuid4(),
            content="Test content",
            original_content="Test content",
            chunk_index=0,
            start_char=0,
            end_char=12,
            embedding=Embedding.from_openai([0.1, 0.2, 0.3])
        )
        
        search_result = SearchResult(
            chunk=chunk,
            similarity_score=0.7,
            distance=0.3,
            metadata={}
        )
        
        references = search_service.convert_results_to_references([search_result])
        
        assert len(references) == 1
        ref = references[0]
        assert ref.source == "unknown"
        assert ref.page is None
        assert ref.similarity_score == 0.7
        assert ref.excerpt == "Test content"
    
    @pytest.mark.asyncio
    async def test_search_similar_content_exception_handling(self, search_service, mock_vector_repository):
        query_embedding = Embedding.from_openai([0.1, 0.2, 0.3])
        mock_vector_repository.search_similar_chunks.side_effect = Exception("Database error")
        
        with pytest.raises(Exception) as exc_info:
            await search_service.search_similar_content(
                query="exception test",
                query_embedding=query_embedding
            )
        
        assert "Failed to search similar content" in str(exc_info.value)
    
    def test_create_excerpt_long_content(self, search_service):
        long_content = "This is a very long content that should be truncated because it exceeds the maximum length limit that we set for excerpts in our search results to keep them readable and concise."
        
        excerpt = search_service._create_excerpt(long_content, max_length=50)
        
        assert len(excerpt) <= 53
        assert excerpt.endswith("...")
        assert not excerpt.endswith(" ...")
    
    def test_calculate_relevance_score(self, search_service):
        score = search_service.calculate_relevance_score(0.8)
        assert score == 0.8
        
        score = search_service.calculate_relevance_score(0.8, document_popularity=1.2, recency_factor=0.9)
        assert score == 0.8 * 1.2 * 0.9
