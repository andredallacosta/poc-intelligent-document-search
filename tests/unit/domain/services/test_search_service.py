from unittest.mock import AsyncMock, Mock

import pytest

from domain.entities.message import DocumentReference
from domain.repositories.vector_repository import VectorRepository
from domain.services.search_service import SearchService


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
    async def test_search_similar_content_success(
        self,
        search_service,
        mock_vector_repository,
        sample_embedding,
        sample_search_results,
    ):
        mock_vector_repository.search_similar_chunks = AsyncMock(
            return_value=sample_search_results
        )
        results = await search_service.search_similar_content(
            query="test query",
            query_embedding=sample_embedding,
            n_results=3,
            similarity_threshold=0.7,
        )
        assert len(results) == 3
        mock_vector_repository.search_similar_chunks.assert_called_once_with(
            query_embedding=sample_embedding,
            n_results=3,
            similarity_threshold=0.7,
            metadata_filter=None,
        )

    @pytest.mark.asyncio
    async def test_search_similar_content_with_metadata_filter(
        self, search_service, mock_vector_repository, sample_embedding
    ):
        metadata_filter = {"document_type": "pdf"}
        mock_vector_repository.search_similar_chunks = AsyncMock(return_value=[])
        await search_service.search_similar_content(
            query="test query with metadata",
            query_embedding=sample_embedding,
            n_results=5,
            similarity_threshold=0.8,
            metadata_filter=metadata_filter,
        )
        mock_vector_repository.search_similar_chunks.assert_called_once_with(
            query_embedding=sample_embedding,
            n_results=5,
            similarity_threshold=0.8,
            metadata_filter=metadata_filter,
        )

    @pytest.mark.asyncio
    async def test_search_similar_content_empty_results(
        self, search_service, mock_vector_repository, sample_embedding
    ):
        mock_vector_repository.search_similar_chunks = AsyncMock(return_value=[])
        results = await search_service.search_similar_content(
            query="empty test query", query_embedding=sample_embedding, n_results=3
        )
        assert results == []

    def test_convert_results_to_references(self, search_service, sample_search_results):
        references = search_service.convert_results_to_references(sample_search_results)
        assert len(references) == 3
        for i, reference in enumerate(references):
            assert isinstance(reference, DocumentReference)
            assert reference.document_id == sample_search_results[i].chunk.document_id
            assert reference.chunk_id == sample_search_results[i].chunk.id
            assert (
                reference.similarity_score == sample_search_results[i].similarity_score
            )

    def test_convert_empty_results_to_references(self, search_service):
        references = search_service.convert_results_to_references([])
        assert references == []

    def test_calculate_relevance_score_basic(self, search_service):
        score = search_service.calculate_relevance_score(0.8)
        assert score == 0.8

    def test_calculate_relevance_score_with_factors(self, search_service):
        score = search_service.calculate_relevance_score(
            similarity_score=0.8, document_popularity=1.2, recency_factor=0.9
        )
        expected = 0.8 * 1.2 * 0.9
        assert score == pytest.approx(expected, abs=1e-6)

    @pytest.mark.asyncio
    async def test_search_by_document_type(
        self, search_service, mock_vector_repository, sample_embedding
    ):
        mock_vector_repository.search_similar_chunks = AsyncMock(return_value=[])
        await search_service.search_by_document_type(
            query="test query for pdf",
            query_embedding=sample_embedding,
            document_type="pdf",
            n_results=3,
        )
        mock_vector_repository.search_similar_chunks.assert_called_once()
        call_args = mock_vector_repository.search_similar_chunks.call_args
        assert call_args[1]["metadata_filter"] == {"file_type": "pdf"}

    @pytest.mark.asyncio
    async def test_search_by_source(
        self, search_service, mock_vector_repository, sample_embedding
    ):
        mock_vector_repository.search_similar_chunks = AsyncMock(return_value=[])
        await search_service.search_by_source(
            query="test query for source",
            query_embedding=sample_embedding,
            source="test_doc.pdf",
            n_results=5,
        )
        mock_vector_repository.search_similar_chunks.assert_called_once()
        call_args = mock_vector_repository.search_similar_chunks.call_args
        assert call_args[1]["metadata_filter"] == {"source": "test_doc.pdf"}

    @pytest.mark.asyncio
    async def test_search_with_custom_parameters(
        self, search_service, mock_vector_repository, sample_embedding
    ):
        mock_vector_repository.search_similar_chunks = AsyncMock(return_value=[])
        await search_service.search_similar_content(
            query="custom parameters test",
            query_embedding=sample_embedding,
            n_results=10,
            similarity_threshold=0.9,
            metadata_filter={"language": "pt-BR"},
        )
        mock_vector_repository.search_similar_chunks.assert_called_once_with(
            query_embedding=sample_embedding,
            n_results=10,
            similarity_threshold=0.9,
            metadata_filter={"language": "pt-BR"},
        )

    @pytest.mark.asyncio
    async def test_search_similar_content_with_threshold_service(
        self, mock_vector_repository, sample_embedding
    ):
        mock_threshold_service = Mock()
        mock_threshold_service.get_threshold_for_query = Mock(return_value=0.75)
        search_service = SearchService(
            vector_repository=mock_vector_repository,
            threshold_service=mock_threshold_service,
        )
        mock_vector_repository.search_similar_chunks = AsyncMock(return_value=[])
        await search_service.search_similar_content(
            query="test with threshold service",
            query_embedding=sample_embedding,
            n_results=3,
        )
        mock_threshold_service.get_threshold_for_query.assert_called_once_with(
            "test with threshold service"
        )
        mock_vector_repository.search_similar_chunks.assert_called_once_with(
            query_embedding=sample_embedding,
            n_results=3,
            similarity_threshold=0.75,
            metadata_filter=None,
        )

    @pytest.mark.asyncio
    async def test_search_similar_content_default_threshold(
        self, search_service, mock_vector_repository, sample_embedding
    ):
        mock_vector_repository.search_similar_chunks = AsyncMock(return_value=[])
        await search_service.search_similar_content(
            query="test default threshold",
            query_embedding=sample_embedding,
            n_results=3,
        )
        mock_vector_repository.search_similar_chunks.assert_called_once_with(
            query_embedding=sample_embedding,
            n_results=3,
            similarity_threshold=0.45,
            metadata_filter=None,
        )

    @pytest.mark.asyncio
    async def test_search_similar_content_exception_handling(
        self, search_service, mock_vector_repository, sample_embedding
    ):
        from domain.exceptions.chat_exceptions import SearchError

        mock_vector_repository.search_similar_chunks = AsyncMock(
            side_effect=Exception("Database error")
        )
        with pytest.raises(SearchError, match="Failed to search similar content"):
            await search_service.search_similar_content(
                query="error test query", query_embedding=sample_embedding, n_results=3
            )

    def test_filter_and_rank_results(self, search_service, mock_data_factory):
        results = []
        for i, score in enumerate([0.9, 0.3, 0.8, 0.2, 0.7]):
            result = mock_data_factory.create_search_result(similarity_score=score)
            results.append(result)
        filtered_results = search_service._filter_and_rank_results(
            results, threshold=0.5
        )
        assert len(filtered_results) == 3
        assert filtered_results[0].similarity_score == 0.9
        assert filtered_results[1].similarity_score == 0.8
        assert filtered_results[2].similarity_score == 0.7

    def test_filter_and_rank_results_empty(self, search_service):
        filtered_results = search_service._filter_and_rank_results([], threshold=0.5)
        assert filtered_results == []

    def test_filter_and_rank_results_all_below_threshold(
        self, search_service, mock_data_factory
    ):
        results = []
        for score in [0.3, 0.2, 0.1]:
            result = mock_data_factory.create_search_result(similarity_score=score)
            results.append(result)
        filtered_results = search_service._filter_and_rank_results(
            results, threshold=0.5
        )
        assert filtered_results == []

    def test_create_excerpt_short_content(self, search_service):
        content = "This is a short content"
        excerpt = search_service._create_excerpt(content, max_length=200)
        assert excerpt == content

    def test_create_excerpt_long_content(self, search_service):
        content = "This is a very long content that exceeds the maximum length and should be truncated properly at word boundaries"
        excerpt = search_service._create_excerpt(content, max_length=50)
        assert len(excerpt) <= 53
        assert excerpt.endswith("...")
        assert not excerpt[:-3].endswith(" ")

    def test_create_excerpt_exact_length(self, search_service):
        content = "This is exactly fifty characters long content here"
        excerpt = search_service._create_excerpt(content, max_length=50)
        assert excerpt == content

    def test_convert_results_to_references_with_metadata(
        self, search_service, mock_data_factory
    ):
        from domain.repositories.vector_repository import SearchResult

        results = []
        for i in range(2):
            chunk = mock_data_factory.create_document_chunk(
                content=f"Chunk {i} content"
            )
            result = SearchResult(
                chunk=chunk,
                similarity_score=0.8 + i * 0.1,
                distance=0.2 - i * 0.1,
                metadata={"source": f"doc_{i}.pdf", "page": i + 1},
            )
            results.append(result)
        references = search_service.convert_results_to_references(results)
        assert len(references) == 2
        for i, reference in enumerate(references):
            assert reference.source == f"doc_{i}.pdf"
            assert reference.page == i + 1
            assert reference.similarity_score == 0.8 + i * 0.1

    def test_convert_results_to_references_no_metadata(
        self, search_service, mock_data_factory
    ):
        from domain.repositories.vector_repository import SearchResult

        chunk = mock_data_factory.create_document_chunk(content="Test content")
        result = SearchResult(
            chunk=chunk, similarity_score=0.8, distance=0.2, metadata=None
        )
        references = search_service.convert_results_to_references([result])
        assert len(references) == 1
        assert references[0].source == "unknown"
        assert references[0].page is None

    def test_convert_results_to_references_partial_metadata(
        self, search_service, mock_data_factory
    ):
        from domain.repositories.vector_repository import SearchResult

        chunk = mock_data_factory.create_document_chunk(content="Test content")
        result = SearchResult(
            chunk=chunk,
            similarity_score=0.8,
            distance=0.2,
            metadata={"source": "test.pdf"},
        )
        references = search_service.convert_results_to_references([result])
        assert len(references) == 1
        assert references[0].source == "test.pdf"
        assert references[0].page is None
