from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from application.dto.chat_dto import ChatRequestDTO, ChatResponseDTO
from application.interfaces.llm_service import LLMServiceInterface
from application.use_cases.chat_with_documents import ChatWithDocumentsUseCase
from domain.entities.chat_session import ChatSession
from domain.entities.message import Message, MessageRole
from domain.exceptions.chat_exceptions import ChatError
from domain.services.chat_service import ChatService
from domain.services.search_service import SearchService
from domain.services.token_limit_service import TokenLimitService


class TestChatWithDocumentsUseCase:
    @pytest.fixture
    def mock_chat_service(self):
        return Mock(spec=ChatService)

    @pytest.fixture
    def mock_search_service(self):
        return Mock(spec=SearchService)

    @pytest.fixture
    def mock_llm_service(self):
        return Mock(spec=LLMServiceInterface)

    @pytest.fixture
    def mock_token_limit_service(self):
        return Mock(spec=TokenLimitService)

    @pytest.fixture
    def use_case(
        self,
        mock_chat_service,
        mock_search_service,
        mock_llm_service,
        mock_token_limit_service,
    ):
        return ChatWithDocumentsUseCase(
            chat_service=mock_chat_service,
            search_service=mock_search_service,
            llm_service=mock_llm_service,
            token_limit_service=mock_token_limit_service,
        )

    @pytest.fixture
    def chat_request_new_session(self):
        return ChatRequestDTO(
            message="Como escrever um ofício oficial?",
            session_id=None,
            metadata={"source": "test"},
        )

    @pytest.fixture
    def chat_request_existing_session(self):
        return ChatRequestDTO(message="E o cabeçalho?", session_id=uuid4(), metadata={})

    @pytest.fixture
    def mock_session(self):
        session = Mock(spec=ChatSession)
        session.id = uuid4()
        return session

    @pytest.fixture
    def mock_user_message(self):
        message = Mock(spec=Message)
        message.id = uuid4()
        message.role = MessageRole.USER
        message.content = "Test message"
        return message

    @pytest.fixture
    def mock_assistant_message(self):
        message = Mock(spec=Message)
        message.id = uuid4()
        message.role = MessageRole.ASSISTANT
        message.content = "Test response"
        return message

    @pytest.fixture
    def mock_search_results(self, mock_data_factory):
        return mock_data_factory.create_search_results(2)

    @pytest.fixture
    def mock_document_references(self, sample_document_reference):
        return [sample_document_reference]

    @pytest.fixture
    def mock_llm_response(self):
        return {
            "content": "Para escrever um ofício oficial, você deve seguir a estrutura formal...",
            "model": "gpt-4o-mini",
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 75,
                "total_tokens": 225,
            },
        }

    @pytest.mark.asyncio
    async def test_execute_new_session_success(
        self,
        use_case,
        chat_request_new_session,
        mock_chat_service,
        mock_search_service,
        mock_llm_service,
        mock_session,
        mock_user_message,
        mock_assistant_message,
        mock_search_results,
        mock_document_references,
        mock_llm_response,
        sample_embedding,
    ):
        mock_chat_service.create_session = AsyncMock(return_value=mock_session)
        mock_chat_service.add_user_message = AsyncMock(return_value=mock_user_message)
        mock_chat_service.add_assistant_message = AsyncMock(
            return_value=mock_assistant_message
        )
        mock_chat_service.get_conversation_history = AsyncMock(return_value=[])
        mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_llm_service.generate_response = AsyncMock(return_value=mock_llm_response)
        mock_search_service.search_similar_content = AsyncMock(
            return_value=mock_search_results
        )
        mock_search_service.convert_results_to_references = Mock(
            return_value=mock_document_references
        )
        response = await use_case.execute(chat_request_new_session)
        assert isinstance(response, ChatResponseDTO)
        assert response.response == mock_llm_response["content"]
        assert response.session_id == mock_session.id
        assert len(response.sources) == 1
        assert response.processing_time > 0
        assert response.token_usage == mock_llm_response["usage"]
        mock_chat_service.create_session.assert_called_once()
        mock_chat_service.add_user_message.assert_called_once()
        mock_chat_service.add_assistant_message.assert_called_once()
        mock_llm_service.generate_embedding.assert_called_once_with(
            chat_request_new_session.message
        )
        mock_llm_service.generate_response.assert_called_once()
        mock_search_service.search_similar_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_existing_session_success(
        self,
        use_case,
        chat_request_existing_session,
        mock_chat_service,
        mock_search_service,
        mock_llm_service,
        mock_session,
        mock_user_message,
        mock_assistant_message,
        mock_search_results,
        mock_document_references,
        mock_llm_response,
    ):
        mock_chat_service.get_session = AsyncMock(return_value=mock_session)
        mock_chat_service.add_user_message = AsyncMock(return_value=mock_user_message)
        mock_chat_service.add_assistant_message = AsyncMock(
            return_value=mock_assistant_message
        )
        mock_chat_service.get_conversation_history = AsyncMock(
            return_value=[mock_user_message]
        )
        mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_llm_service.generate_response = AsyncMock(return_value=mock_llm_response)
        mock_search_service.search_similar_content = AsyncMock(
            return_value=mock_search_results
        )
        mock_search_service.convert_results_to_references = Mock(
            return_value=mock_document_references
        )
        response = await use_case.execute(chat_request_existing_session)
        assert isinstance(response, ChatResponseDTO)
        assert response.session_id == mock_session.id
        mock_chat_service.get_session.assert_called_once_with(
            chat_request_existing_session.session_id
        )
        mock_chat_service.create_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_no_search_results(
        self,
        use_case,
        chat_request_new_session,
        mock_chat_service,
        mock_search_service,
        mock_llm_service,
        mock_session,
        mock_user_message,
        mock_assistant_message,
        mock_llm_response,
    ):
        mock_chat_service.create_session = AsyncMock(return_value=mock_session)
        mock_chat_service.add_user_message = AsyncMock(return_value=mock_user_message)
        mock_chat_service.add_assistant_message = AsyncMock(
            return_value=mock_assistant_message
        )
        mock_chat_service.get_conversation_history = AsyncMock(return_value=[])
        mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_llm_service.generate_response = AsyncMock(return_value=mock_llm_response)
        mock_search_service.search_similar_content = AsyncMock(return_value=[])
        mock_search_service.convert_results_to_references = Mock(return_value=[])
        response = await use_case.execute(chat_request_new_session)
        assert isinstance(response, ChatResponseDTO)
        assert len(response.sources) == 0
        assert response.metadata["search_results_count"] == 0

    @pytest.mark.asyncio
    async def test_execute_llm_context_preparation(
        self,
        use_case,
        chat_request_new_session,
        mock_chat_service,
        mock_search_service,
        mock_llm_service,
        mock_session,
        mock_user_message,
        mock_assistant_message,
        mock_search_results,
        mock_document_references,
        mock_llm_response,
    ):
        conversation_history = [mock_user_message]
        mock_chat_service.create_session = AsyncMock(return_value=mock_session)
        mock_chat_service.add_user_message = AsyncMock(return_value=mock_user_message)
        mock_chat_service.add_assistant_message = AsyncMock(
            return_value=mock_assistant_message
        )
        mock_chat_service.get_conversation_history = AsyncMock(
            return_value=conversation_history
        )
        mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_llm_service.generate_response = AsyncMock(return_value=mock_llm_response)
        mock_search_service.search_similar_content = AsyncMock(
            return_value=mock_search_results
        )
        mock_search_service.convert_results_to_references = Mock(
            return_value=mock_document_references
        )
        await use_case.execute(chat_request_new_session)
        call_args = mock_llm_service.generate_response.call_args
        messages = call_args[1]["messages"]
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert (
            "documentos relevantes" in messages[0]["content"].lower()
            or "nenhum documento" in messages[0]["content"].lower()
        )
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == chat_request_new_session.message

    @pytest.mark.asyncio
    async def test_execute_chat_error_handling(
        self,
        use_case,
        chat_request_new_session,
        mock_chat_service,
        mock_search_service,
        mock_llm_service,
    ):
        mock_chat_service.create_session = AsyncMock(
            side_effect=Exception("Database error")
        )
        with pytest.raises(ChatError, match="Failed to process chat request"):
            await use_case.execute(chat_request_new_session)

    @pytest.mark.asyncio
    async def test_execute_search_parameters(
        self,
        use_case,
        chat_request_new_session,
        mock_chat_service,
        mock_search_service,
        mock_llm_service,
        mock_session,
        mock_user_message,
        mock_assistant_message,
        mock_llm_response,
    ):
        mock_chat_service.create_session = AsyncMock(return_value=mock_session)
        mock_chat_service.add_user_message = AsyncMock(return_value=mock_user_message)
        mock_chat_service.add_assistant_message = AsyncMock(
            return_value=mock_assistant_message
        )
        mock_chat_service.get_conversation_history = AsyncMock(return_value=[])
        mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_llm_service.generate_response = AsyncMock(return_value=mock_llm_response)
        mock_search_service.search_similar_content = AsyncMock(return_value=[])
        mock_search_service.convert_results_to_references = Mock(return_value=[])
        await use_case.execute(chat_request_new_session)
        mock_search_service.search_similar_content.assert_called_once()
        call_args = mock_search_service.search_similar_content.call_args
        assert call_args[1]["query"] == "Como escrever um ofício oficial?"
        assert call_args[1]["n_results"] == 5
        # similarity_threshold is None (uses adaptive threshold)
