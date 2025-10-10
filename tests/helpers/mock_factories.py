from datetime import datetime
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from application.dto.chat_dto import (
    ChatRequestDTO,
    ChatResponseDTO,
    DocumentReferenceDTO,
)
from domain.entities.chat_session import ChatSession
from domain.entities.document import Document, DocumentChunk
from domain.entities.message import DocumentReference, Message, MessageRole
from domain.value_objects.document_metadata import DocumentMetadata
from domain.value_objects.embedding import Embedding


class MockFactory:
    """Factory for creating mock objects and test data"""

    @staticmethod
    def create_embedding(dimensions: int = 1536, model: str = "openai") -> Embedding:
        """Create a mock embedding with specified dimensions"""
        vector = [0.1] * dimensions
        return (
            Embedding.from_openai(vector)
            if model == "openai"
            else Embedding.from_custom(vector, model)
        )

    @staticmethod
    def create_document_metadata(
        source: str = "test_document.pdf",
        file_type: str = "pdf",
        file_size: int = 1024000,
        page_count: int = 10,
        author: str = "Test Author",
        title: str = "Test Document",
        language: str = "pt-BR",
    ) -> DocumentMetadata:
        """Create mock document metadata"""
        return DocumentMetadata(
            source=source,
            file_type=file_type,
            file_size=file_size,
            page_count=page_count,
            author=author,
            title=title,
            language=language,
            creation_date=datetime.utcnow(),
        )

    @staticmethod
    def create_document_chunk(
        content: str = "Test chunk content",
        chunk_index: int = 0,
        document_id: Optional[str] = None,
        with_embedding: bool = True,
    ) -> DocumentChunk:
        """Create a mock document chunk"""
        embedding = MockFactory.create_embedding() if with_embedding else None
        return DocumentChunk(
            id=uuid4(),
            document_id=uuid4() if document_id is None else document_id,
            content=content,
            original_content=content,
            chunk_index=chunk_index,
            start_char=chunk_index * 100,
            end_char=(chunk_index + 1) * 100,
            embedding=embedding,
        )

    @staticmethod
    def create_document(
        title: str = "Test Document",
        content: str = "Test document content",
        chunk_count: int = 3,
    ) -> Document:
        """Create a mock document with specified number of chunks"""
        metadata = MockFactory.create_document_metadata(title=title)
        doc = Document(
            id=uuid4(),
            title=title,
            content=content,
            file_path=f"/test/{title.lower().replace(' ', '_')}.pdf",
            metadata=metadata,
            chunks=[],
        )
        for i in range(chunk_count):
            chunk = MockFactory.create_document_chunk(
                content=f"Chunk {i} content from {title}",
                chunk_index=i,
                document_id=doc.id,
            )
            doc.add_chunk(chunk)
        return doc

    @staticmethod
    def create_message(
        role: MessageRole = MessageRole.USER,
        content: str = "Test message",
        session_id: Optional[str] = None,
        with_references: bool = False,
    ) -> Message:
        """Create a mock message"""
        references = []
        if with_references:
            references = [MockFactory.create_document_reference()]
        return Message(
            id=uuid4(),
            session_id=uuid4() if session_id is None else session_id,
            role=role,
            content=content,
            document_references=references,
            metadata={"test": True},
        )

    @staticmethod
    def create_chat_session(message_count: int = 0) -> ChatSession:
        """Create a mock chat session with specified number of messages"""
        session = ChatSession(id=uuid4())
        for i in range(message_count):
            role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            message = MockFactory.create_message(
                role=role, content=f"Message {i}", session_id=session.id
            )
            session.add_message(message)
        return session

    @staticmethod
    def create_document_reference(
        similarity_score: float = 0.85, source: str = "test_document.pdf", page: int = 1
    ) -> DocumentReference:
        """Create a mock document reference"""
        return DocumentReference(
            document_id=uuid4(),
            chunk_id=uuid4(),
            source=source,
            page=page,
            similarity_score=similarity_score,
            excerpt="This is a test excerpt from the document.",
        )

    @staticmethod
    def create_search_result(
        similarity_score: float = 0.9, chunk_content: str = "Test search result content"
    ):
        """Create a mock search result"""
        from domain.repositories.vector_repository import SearchResult

        chunk = MockFactory.create_document_chunk(content=chunk_content)
        return SearchResult(
            chunk=chunk,
            similarity_score=similarity_score,
            distance=1.0 - similarity_score,
            metadata={"source": "test_document.pdf", "page": 1},
        )

    @staticmethod
    def create_search_results(count: int = 3):
        """Create multiple mock search results"""
        results = []
        for i in range(count):
            result = MockFactory.create_search_result(
                similarity_score=0.9 - (i * 0.1),
                chunk_content=f"Search result {i} content",
            )
            results.append(result)
        return results

    @staticmethod
    def create_chat_request_dto(
        message: str = "Test message",
        session_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> ChatRequestDTO:
        """Create a mock chat request DTO"""
        return ChatRequestDTO(
            message=message, session_id=session_id, metadata=metadata or {}
        )

    @staticmethod
    def create_chat_response_dto(
        response: str = "Test response",
        session_id: Optional[str] = None,
        sources_count: int = 1,
    ) -> ChatResponseDTO:
        """Create a mock chat response DTO"""
        sources = []
        for i in range(sources_count):
            source = DocumentReferenceDTO(
                document_id=uuid4(),
                chunk_id=uuid4(),
                source=f"test_doc_{i}.pdf",
                page=1,
                similarity_score=0.9 - (i * 0.1),
                excerpt=f"Test excerpt {i}",
            )
            sources.append(source)
        return ChatResponseDTO(
            response=response,
            session_id=uuid4() if session_id is None else session_id,
            sources=sources,
            metadata={"test": True},
            processing_time=1.5,
            token_usage={
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        )

    @staticmethod
    def create_llm_response(
        content: str = "Test LLM response", model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """Create a mock LLM response"""
        return {
            "content": content,
            "model": model,
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        }


class MockServiceFactory:
    """Factory for creating mock services"""

    @staticmethod
    def create_mock_chat_service():
        """Create a mock chat service with common methods"""
        mock = Mock()
        mock.create_session = AsyncMock()
        mock.get_session = AsyncMock()
        mock.add_user_message = AsyncMock()
        mock.add_assistant_message = AsyncMock()
        mock.get_conversation_history = AsyncMock()
        return mock

    @staticmethod
    def create_mock_search_service():
        """Create a mock search service with common methods"""
        mock = Mock()
        mock.search_similar_content = AsyncMock()
        mock.convert_results_to_references = Mock()
        return mock

    @staticmethod
    def create_mock_llm_service():
        """Create a mock LLM service with common methods"""
        mock = Mock()
        mock.generate_embedding = AsyncMock()
        mock.generate_response = AsyncMock()
        mock.generate_embeddings_batch = AsyncMock()
        return mock

    @staticmethod
    def create_mock_vector_repository():
        """Create a mock vector repository with common methods"""
        mock = Mock()
        mock.add_chunk_embedding = AsyncMock()
        mock.search_similar_chunks = AsyncMock()
        mock.delete_chunk_embedding = AsyncMock()
        mock.delete_document_embeddings = AsyncMock()
        mock.update_chunk_embedding = AsyncMock()
        mock.get_embedding_by_chunk_id = AsyncMock()
        mock.count_embeddings = AsyncMock()
        mock.embedding_exists = AsyncMock()
        return mock

    @staticmethod
    def create_mock_session_repository():
        """Create a mock session repository with common methods"""
        mock = Mock()
        mock.save_session = AsyncMock()
        mock.get_session = AsyncMock()
        mock.delete_session = AsyncMock()
        mock.session_exists = AsyncMock()
        mock.update_session = AsyncMock()
        return mock
