import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException
from uuid import uuid4

from interface.api.v1.endpoints.chat import ask_question, health_check, get_available_models
from interface.schemas.chat import ChatRequest, ChatResponse
from application.use_cases.chat_with_documents import ChatWithDocumentsUseCase
from application.dto.chat_dto import ChatRequestDTO, ChatResponseDTO, DocumentReferenceDTO
from domain.exceptions.chat_exceptions import (
    ChatError, 
    SessionNotFoundError, 
    RateLimitExceededError,
    InvalidMessageError
)

class TestChatEndpoints:
    
    @pytest.fixture
    def mock_chat_use_case(self):
        return Mock(spec=ChatWithDocumentsUseCase)
    
    @pytest.fixture
    def sample_chat_request(self):
        return ChatRequest(
            message="What is the capital of France?",
            session_id=None,
            metadata={}
        )
    
    @pytest.fixture
    def sample_chat_response_dto(self):
        session_id = uuid4()
        source = DocumentReferenceDTO(
            document_id=uuid4(),
            chunk_id=uuid4(),
            source="geography.pdf",
            page=1,
            similarity_score=0.9,
            excerpt="Paris is the capital of France"
        )
        
        return ChatResponseDTO(
            response="The capital of France is Paris.",
            session_id=session_id,
            sources=[source],
            metadata={"search_results": 1},
            processing_time=1.2,
            token_usage={"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30}
        )
    
    @pytest.mark.asyncio
    async def test_ask_question_success(self, sample_chat_request, sample_chat_response_dto, mock_chat_use_case):
        with patch('interface.dependencies.container.create_chat_use_case', return_value=mock_chat_use_case):
            mock_chat_use_case.execute = AsyncMock(return_value=sample_chat_response_dto)
            
            response = await ask_question(sample_chat_request)
            
            assert isinstance(response, ChatResponse)
            assert response.response == "The capital of France is Paris."
            assert response.session_id == sample_chat_response_dto.session_id
            assert len(response.sources) == 1
            assert response.sources[0].source == "geography.pdf"
            assert response.processing_time == 1.2
            
            mock_chat_use_case.execute.assert_called_once()
            call_args = mock_chat_use_case.execute.call_args[0][0]
            assert isinstance(call_args, ChatRequestDTO)
            assert call_args.message == "What is the capital of France?"
            assert call_args.session_id is None
            assert call_args.metadata == {}
    
    @pytest.mark.asyncio
    async def test_ask_question_with_session_id(self, mock_chat_use_case, sample_chat_response_dto):
        session_id = uuid4()
        request = ChatRequest(
            message="Continue the conversation",
            session_id=session_id,
            metadata={"context": "follow-up"}
        )
        
        with patch('interface.dependencies.container.create_chat_use_case', return_value=mock_chat_use_case):
            mock_chat_use_case.execute = AsyncMock(return_value=sample_chat_response_dto)
            
            response = await ask_question(request)
            
            assert isinstance(response, ChatResponse)
            
            call_args = mock_chat_use_case.execute.call_args[0][0]
            assert call_args.session_id == session_id
            assert call_args.metadata == {"context": "follow-up"}
    
    @pytest.mark.asyncio
    async def test_ask_question_invalid_message_error(self, mock_chat_use_case):
        request = ChatRequest(message="Test message")
        
        with patch('interface.dependencies.container.create_chat_use_case', return_value=mock_chat_use_case):
            mock_chat_use_case.execute = AsyncMock(side_effect=InvalidMessageError("Message too short"))
            
            with pytest.raises(HTTPException) as exc_info:
                await ask_question(request)
            
            assert exc_info.value.status_code == 400
            assert "Message too short" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_ask_question_session_not_found_error(self, mock_chat_use_case):
        session_id = uuid4()
        request = ChatRequest(message="Test message", session_id=session_id)
        
        with patch('interface.dependencies.container.create_chat_use_case', return_value=mock_chat_use_case):
            mock_chat_use_case.execute = AsyncMock(side_effect=SessionNotFoundError(f"Session {session_id} not found"))
            
            with pytest.raises(HTTPException) as exc_info:
                await ask_question(request)
            
            assert exc_info.value.status_code == 404
            assert "not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_ask_question_rate_limit_exceeded_error(self, mock_chat_use_case):
        request = ChatRequest(message="Test message")
        
        with patch('interface.dependencies.container.create_chat_use_case', return_value=mock_chat_use_case):
            mock_chat_use_case.execute = AsyncMock(side_effect=RateLimitExceededError("Rate limit exceeded"))
            
            with pytest.raises(HTTPException) as exc_info:
                await ask_question(request)
            
            assert exc_info.value.status_code == 429
            assert "Rate limit exceeded" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_ask_question_generic_chat_error(self, mock_chat_use_case):
        request = ChatRequest(message="Test message")
        
        with patch('interface.dependencies.container.create_chat_use_case', return_value=mock_chat_use_case):
            mock_chat_use_case.execute = AsyncMock(side_effect=ChatError("Generic chat error"))
            
            with pytest.raises(HTTPException) as exc_info:
                await ask_question(request)
            
            assert exc_info.value.status_code == 500
            assert "Generic chat error" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_ask_question_unexpected_error(self, mock_chat_use_case):
        request = ChatRequest(message="Test message")
        
        with patch('interface.dependencies.container.create_chat_use_case', return_value=mock_chat_use_case):
            mock_chat_use_case.execute = AsyncMock(side_effect=Exception("Unexpected error"))
            
            with pytest.raises(HTTPException) as exc_info:
                await ask_question(request)
            
            assert exc_info.value.status_code == 500
            assert "Internal server error" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        response = await health_check()
        
        assert response == {"status": "healthy", "service": "chat"}
    
    def test_chat_request_to_dto_conversion(self, sample_chat_request):
        chat_request_dto = ChatRequestDTO(
            message=sample_chat_request.message,
            session_id=sample_chat_request.session_id,
            metadata=sample_chat_request.metadata
        )
        
        assert chat_request_dto.message == sample_chat_request.message
        assert chat_request_dto.session_id == sample_chat_request.session_id
        assert chat_request_dto.metadata == sample_chat_request.metadata
    
    def test_chat_response_dto_to_schema_conversion(self, sample_chat_response_dto):
        response = ChatResponse(
            response=sample_chat_response_dto.response,
            session_id=sample_chat_response_dto.session_id,
            sources=[
                {
                    "document_id": source.document_id,
                    "chunk_id": source.chunk_id,
                    "source": source.source,
                    "page": source.page,
                    "similarity_score": source.similarity_score,
                    "excerpt": source.excerpt
                }
                for source in sample_chat_response_dto.sources
            ],
            metadata=sample_chat_response_dto.metadata,
            processing_time=sample_chat_response_dto.processing_time,
            token_usage=sample_chat_response_dto.token_usage
        )
        
        assert response.response == sample_chat_response_dto.response
        assert response.session_id == sample_chat_response_dto.session_id
        assert len(response.sources) == len(sample_chat_response_dto.sources)
        assert response.processing_time == sample_chat_response_dto.processing_time
        assert response.token_usage == sample_chat_response_dto.token_usage
    
    @pytest.mark.asyncio
    async def test_get_available_models(self):
        response = await get_available_models()
        
        assert "models" in response
        assert len(response["models"]) == 1
        assert response["models"][0]["id"] == "gpt-4o-mini"
        assert response["models"][0]["name"] == "GPT-4o Mini"
        assert response["models"][0]["description"] == "Fast and cost-effective model"
        assert response["models"][0]["max_tokens"] == 4096
    
    @pytest.mark.asyncio
    async def test_create_chat_use_case_dependency_injection(self):
        from unittest.mock import patch, AsyncMock
        
        with patch('interface.dependencies.container.create_chat_use_case') as mock_create_use_case:
            mock_use_case = Mock(spec=ChatWithDocumentsUseCase)
            mock_create_use_case.return_value = mock_use_case
            
            from interface.dependencies.container import create_chat_use_case
            result = await create_chat_use_case()
            
            assert result == mock_use_case
