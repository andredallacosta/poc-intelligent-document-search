from uuid import uuid4

import pytest
from pydantic import ValidationError

from interface.schemas.chat import (
    ChatRequest,
    ChatResponse,
    DocumentSource,
    ErrorResponse,
)


class TestChatRequest:
    def test_create_chat_request_minimal(self):
        request = ChatRequest(message="Hello world")
        assert request.message == "Hello world"
        assert request.session_id is None
        assert request.metadata == {}

    def test_create_chat_request_complete(self):
        session_id = uuid4()
        metadata = {"user_id": "123", "context": "test"}
        request = ChatRequest(
            message="Test message", session_id=session_id, metadata=metadata
        )
        assert request.message == "Test message"
        assert request.session_id == session_id
        assert request.metadata == metadata

    def test_chat_request_empty_message_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="")
        assert "at least 1 character" in str(exc_info.value)

    def test_chat_request_whitespace_only_message_succeeds(self):
        request = ChatRequest(message="   ")
        assert request.message == "   "

    def test_chat_request_too_long_message_fails(self):
        long_message = "x" * 2001
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message=long_message)
        assert "at most 2000 characters" in str(exc_info.value)

    def test_chat_request_max_length_message_succeeds(self):
        max_message = "x" * 2000
        request = ChatRequest(message=max_message)
        assert len(request.message) == 2000

    def test_chat_request_json_serialization(self):
        session_id = uuid4()
        request = ChatRequest(
            message="Test message", session_id=session_id, metadata={"key": "value"}
        )
        json_data = request.model_dump()
        assert json_data["message"] == "Test message"
        assert json_data["session_id"] == session_id
        assert json_data["metadata"] == {"key": "value"}


class TestDocumentSource:
    def test_create_document_source_minimal(self):
        doc_id = uuid4()
        chunk_id = uuid4()
        source = DocumentSource(
            document_id=doc_id, chunk_id=chunk_id, source="test.pdf"
        )
        assert source.document_id == doc_id
        assert source.chunk_id == chunk_id
        assert source.source == "test.pdf"
        assert source.page is None
        assert source.similarity_score is None
        assert source.excerpt is None

    def test_create_document_source_complete(self):
        doc_id = uuid4()
        chunk_id = uuid4()
        source = DocumentSource(
            document_id=doc_id,
            chunk_id=chunk_id,
            source="document.pdf",
            page=5,
            similarity_score=0.85,
            excerpt="This is an excerpt from the document",
        )
        assert source.document_id == doc_id
        assert source.chunk_id == chunk_id
        assert source.source == "document.pdf"
        assert source.page == 5
        assert source.similarity_score == 0.85
        assert source.excerpt == "This is an excerpt from the document"

    def test_document_source_similarity_score_validation(self):
        doc_id = uuid4()
        chunk_id = uuid4()
        source1 = DocumentSource(
            document_id=doc_id,
            chunk_id=chunk_id,
            source="test.pdf",
            similarity_score=0.0,
        )
        assert source1.similarity_score == 0.0
        source2 = DocumentSource(
            document_id=doc_id,
            chunk_id=chunk_id,
            source="test.pdf",
            similarity_score=1.0,
        )
        assert source2.similarity_score == 1.0
        with pytest.raises(ValidationError):
            DocumentSource(
                document_id=doc_id,
                chunk_id=chunk_id,
                source="test.pdf",
                similarity_score=-0.1,
            )
        with pytest.raises(ValidationError):
            DocumentSource(
                document_id=doc_id,
                chunk_id=chunk_id,
                source="test.pdf",
                similarity_score=1.1,
            )


class TestChatResponse:
    def test_create_chat_response_minimal(self):
        session_id = uuid4()
        response = ChatResponse(
            response="AI response", session_id=session_id, processing_time=1.5
        )
        assert response.response == "AI response"
        assert response.session_id == session_id
        assert response.sources == []
        assert response.metadata == {}
        assert response.processing_time == 1.5
        assert response.token_usage is None

    def test_create_chat_response_complete(self):
        session_id = uuid4()
        doc_id = uuid4()
        chunk_id = uuid4()
        sources = [
            DocumentSource(
                document_id=doc_id,
                chunk_id=chunk_id,
                source="test.pdf",
                page=1,
                similarity_score=0.9,
                excerpt="Test excerpt",
            )
        ]
        metadata = {"search_count": 3, "model": "gpt-4"}
        token_usage = {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }
        response = ChatResponse(
            response="Complete AI response",
            session_id=session_id,
            sources=sources,
            metadata=metadata,
            processing_time=2.3,
            token_usage=token_usage,
        )
        assert response.response == "Complete AI response"
        assert response.session_id == session_id
        assert response.sources == sources
        assert response.metadata == metadata
        assert response.processing_time == 2.3
        assert response.token_usage == token_usage

    def test_chat_response_negative_processing_time_fails(self):
        session_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            ChatResponse(
                response="Test response", session_id=session_id, processing_time=-1.0
            )
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_chat_response_zero_processing_time_succeeds(self):
        session_id = uuid4()
        response = ChatResponse(
            response="Test response", session_id=session_id, processing_time=0.0
        )
        assert response.processing_time == 0.0

    def test_chat_response_json_serialization(self):
        session_id = uuid4()
        doc_id = uuid4()
        chunk_id = uuid4()
        sources = [
            DocumentSource(document_id=doc_id, chunk_id=chunk_id, source="test.pdf")
        ]
        response = ChatResponse(
            response="Test response",
            session_id=session_id,
            sources=sources,
            processing_time=1.0,
        )
        json_data = response.model_dump()
        assert json_data["response"] == "Test response"
        assert json_data["session_id"] == session_id
        assert len(json_data["sources"]) == 1
        assert json_data["processing_time"] == 1.0


class TestErrorResponse:
    def test_create_error_response_minimal(self):
        error = ErrorResponse(error="Something went wrong")
        assert error.error == "Something went wrong"
        assert error.detail is None
        assert error.error_code is None

    def test_create_error_response_complete(self):
        error = ErrorResponse(
            error="Rate limit exceeded",
            detail="You have exceeded the maximum number of requests per hour",
            error_code="RATE_LIMIT_EXCEEDED",
        )
        assert error.error == "Rate limit exceeded"
        assert (
            error.detail == "You have exceeded the maximum number of requests per hour"
        )
        assert error.error_code == "RATE_LIMIT_EXCEEDED"

    def test_error_response_json_serialization(self):
        error = ErrorResponse(
            error="Validation error",
            detail="Invalid input provided",
            error_code="VALIDATION_ERROR",
        )
        json_data = error.model_dump()
        assert json_data["error"] == "Validation error"
        assert json_data["detail"] == "Invalid input provided"
        assert json_data["error_code"] == "VALIDATION_ERROR"


class TestSchemaIntegration:
    def test_chat_request_to_response_flow(self):
        request = ChatRequest(
            message="What is the capital of France?", metadata={"user_id": "123"}
        )
        session_id = uuid4()
        doc_id = uuid4()
        chunk_id = uuid4()
        source = DocumentSource(
            document_id=doc_id,
            chunk_id=chunk_id,
            source="geography.pdf",
            page=42,
            similarity_score=0.95,
            excerpt="Paris is the capital and largest city of France",
        )
        response = ChatResponse(
            response="The capital of France is Paris.",
            session_id=session_id,
            sources=[source],
            metadata={"search_results": 1},
            processing_time=1.2,
            token_usage={
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "total_tokens": 30,
            },
        )
        assert request.message == "What is the capital of France?"
        assert response.response == "The capital of France is Paris."
        assert len(response.sources) == 1
        assert response.sources[0].source == "geography.pdf"

    def test_all_schemas_json_serializable(self):
        session_id = uuid4()
        doc_id = uuid4()
        chunk_id = uuid4()
        request = ChatRequest(message="Test")
        source = DocumentSource(
            document_id=doc_id, chunk_id=chunk_id, source="test.pdf"
        )
        response = ChatResponse(
            response="Test", session_id=session_id, processing_time=1.0
        )
        error = ErrorResponse(error="Test error")
        request_json = request.model_dump_json()
        source_json = source.model_dump_json()
        response_json = response.model_dump_json()
        error_json = error.model_dump_json()
        assert isinstance(request_json, str)
        assert isinstance(source_json, str)
        assert isinstance(response_json, str)
        assert isinstance(error_json, str)
