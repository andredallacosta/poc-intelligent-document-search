import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from domain.services.chat_service import ChatService
from domain.entities.chat_session import ChatSession
from domain.entities.message import Message, MessageRole, MessageType, DocumentReference
from domain.exceptions.chat_exceptions import (
    SessionNotFoundError,
    InvalidMessageError,
    RateLimitExceededError
)
from domain.repositories.session_repository import SessionRepository, MessageRepository


class TestChatService:
    
    @pytest.fixture
    def mock_session_repository(self):
        return Mock(spec=SessionRepository)
    
    @pytest.fixture
    def mock_message_repository(self):
        return Mock(spec=MessageRepository)
    
    @pytest.fixture
    def chat_service(self, mock_session_repository, mock_message_repository):
        return ChatService(
            session_repository=mock_session_repository,
            message_repository=mock_message_repository,
            max_messages_per_session=100,
            max_daily_messages=50
        )
    
    @pytest.fixture
    def sample_session(self):
        return ChatSession(id=uuid4())
    
    @pytest.fixture
    def sample_message(self, sample_session):
        return Message(
            id=uuid4(),
            session_id=sample_session.id,
            role=MessageRole.USER,
            content="Test message"
        )
    
    @pytest.mark.asyncio
    async def test_create_session(self, chat_service, mock_session_repository):
        # Arrange
        expected_session = ChatSession(id=uuid4())
        mock_session_repository.save_session = AsyncMock(return_value=expected_session)
        
        # Act
        result = await chat_service.create_session()
        
        # Assert
        mock_session_repository.save_session.assert_called_once()
        assert result == expected_session
    
    @pytest.mark.asyncio
    async def test_get_session_success(self, chat_service, mock_session_repository, sample_session):
        # Arrange
        session_id = sample_session.id
        mock_session_repository.find_session_by_id = AsyncMock(return_value=sample_session)
        
        # Act
        result = await chat_service.get_session(session_id)
        
        # Assert
        mock_session_repository.find_session_by_id.assert_called_once_with(session_id)
        assert result == sample_session
    
    @pytest.mark.asyncio
    async def test_get_session_not_found_raises_error(self, chat_service, mock_session_repository):
        # Arrange
        session_id = uuid4()
        mock_session_repository.find_session_by_id = AsyncMock(return_value=None)
        
        # Act & Assert
        with pytest.raises(SessionNotFoundError, match=f"Session '{session_id}' not found"):
            await chat_service.get_session(session_id)
    
    @pytest.mark.asyncio
    async def test_add_user_message_success(
        self, 
        chat_service, 
        mock_session_repository, 
        mock_message_repository,
        sample_session
    ):
        # Arrange
        session_id = sample_session.id
        content = "Hello, world!"
        metadata = {"test": True}
        
        mock_session_repository.find_session_by_id = AsyncMock(return_value=sample_session)
        mock_session_repository.save_session = AsyncMock()
        mock_message_repository.save_message = AsyncMock()
        
        # Act
        result = await chat_service.add_user_message(session_id, content, metadata)
        
        # Assert
        assert result.session_id == session_id
        assert result.role == MessageRole.USER
        assert result.content == content
        assert result.message_type == MessageType.TEXT
        assert result.metadata == metadata
        
        mock_session_repository.save_session.assert_called_once_with(sample_session)
        mock_message_repository.save_message.assert_called_once_with(result)
    
    @pytest.mark.asyncio
    async def test_add_user_message_empty_content_raises_error(
        self, 
        chat_service
    ):
        # Act & Assert
        with pytest.raises(InvalidMessageError, match="Message content cannot be empty"):
            await chat_service.add_user_message(uuid4(), "   ")  # Whitespace only
    
    @pytest.mark.asyncio
    async def test_add_user_message_strips_whitespace(
        self, 
        chat_service, 
        mock_session_repository, 
        mock_message_repository,
        sample_session
    ):
        # Arrange
        session_id = sample_session.id
        content = "  Hello, world!  "
        
        mock_session_repository.find_session_by_id = AsyncMock(return_value=sample_session)
        mock_session_repository.save_session = AsyncMock()
        mock_message_repository.save_message = AsyncMock()
        
        # Act
        result = await chat_service.add_user_message(session_id, content)
        
        # Assert
        assert result.content == "Hello, world!"  # Stripped
    
    @pytest.mark.asyncio
    async def test_add_user_message_rate_limit_exceeded(
        self, 
        mock_session_repository, 
        mock_message_repository
    ):
        # Arrange - Service with low rate limit
        chat_service = ChatService(
            session_repository=mock_session_repository,
            message_repository=mock_message_repository,
            max_messages_per_session=1  # Very low limit
        )
        
        session = ChatSession(id=uuid4())
        # Add a message to reach the limit
        session.add_message(Message(
            id=uuid4(),
            session_id=session.id,
            role=MessageRole.USER,
            content="First message"
        ))
        
        mock_session_repository.find_session_by_id = AsyncMock(return_value=session)
        
        # Act & Assert
        with pytest.raises(RateLimitExceededError, match="Session has reached maximum of 1 messages"):
            await chat_service.add_user_message(session.id, "Second message")
    
    @pytest.mark.asyncio
    async def test_add_assistant_message_success(
        self, 
        chat_service, 
        mock_session_repository, 
        mock_message_repository,
        sample_session
    ):
        # Arrange
        session_id = sample_session.id
        content = "Assistant response"
        document_refs = [DocumentReference(
            document_id=uuid4(),
            chunk_id=uuid4(),
            source="test.pdf"
        )]
        metadata = {"confidence": 0.95}
        
        mock_session_repository.find_session_by_id = AsyncMock(return_value=sample_session)
        mock_session_repository.save_session = AsyncMock()
        mock_message_repository.save_message = AsyncMock()
        
        # Act
        result = await chat_service.add_assistant_message(
            session_id, content, document_refs, metadata
        )
        
        # Assert
        assert result.session_id == session_id
        assert result.role == MessageRole.ASSISTANT
        assert result.content == content
        assert result.document_references == document_refs
        assert result.metadata == metadata
        
        mock_session_repository.save_session.assert_called_once_with(sample_session)
        mock_message_repository.save_message.assert_called_once_with(result)
    
    @pytest.mark.asyncio
    async def test_add_assistant_message_empty_content_raises_error(
        self, 
        chat_service
    ):
        # Act & Assert
        with pytest.raises(InvalidMessageError, match="Message content cannot be empty"):
            await chat_service.add_assistant_message(uuid4(), "")
    
    @pytest.mark.asyncio
    async def test_add_assistant_message_defaults(
        self, 
        chat_service, 
        mock_session_repository, 
        mock_message_repository,
        sample_session
    ):
        # Arrange
        session_id = sample_session.id
        content = "Assistant response"
        
        mock_session_repository.find_session_by_id = AsyncMock(return_value=sample_session)
        mock_session_repository.save_session = AsyncMock()
        mock_message_repository.save_message = AsyncMock()
        
        # Act
        result = await chat_service.add_assistant_message(session_id, content)
        
        # Assert
        assert result.document_references == []
        assert result.metadata == {}
    
    @pytest.mark.asyncio
    async def test_get_conversation_history_success(
        self, 
        chat_service, 
        mock_session_repository, 
        mock_message_repository,
        sample_session,
        sample_message
    ):
        # Arrange
        session_id = sample_session.id
        messages = [sample_message]
        
        mock_session_repository.find_session_by_id = AsyncMock(return_value=sample_session)
        mock_message_repository.find_messages_by_session_id = AsyncMock(return_value=messages)
        
        # Act
        result = await chat_service.get_conversation_history(session_id, limit=10)
        
        # Assert
        mock_session_repository.find_session_by_id.assert_called_once_with(session_id)
        mock_message_repository.find_messages_by_session_id.assert_called_once_with(
            session_id, limit=10
        )
        assert result == messages
    
    @pytest.mark.asyncio
    async def test_get_conversation_history_session_not_found(
        self, 
        chat_service, 
        mock_session_repository
    ):
        # Arrange
        session_id = uuid4()
        mock_session_repository.find_session_by_id = AsyncMock(return_value=None)
        
        # Act & Assert
        with pytest.raises(SessionNotFoundError):
            await chat_service.get_conversation_history(session_id)
    
    @pytest.mark.asyncio
    async def test_deactivate_session_success(
        self, 
        chat_service, 
        mock_session_repository,
        sample_session
    ):
        # Arrange
        session_id = sample_session.id
        mock_session_repository.find_session_by_id = AsyncMock(return_value=sample_session)
        mock_session_repository.save_session = AsyncMock()
        
        # Act
        result = await chat_service.deactivate_session(session_id)
        
        # Assert
        assert result is True
        assert sample_session.is_active is False
        mock_session_repository.save_session.assert_called_once_with(sample_session)
    
    @pytest.mark.asyncio
    async def test_deactivate_session_not_found(
        self, 
        chat_service, 
        mock_session_repository
    ):
        # Arrange
        session_id = uuid4()
        mock_session_repository.find_session_by_id = AsyncMock(return_value=None)
        
        # Act & Assert
        with pytest.raises(SessionNotFoundError):
            await chat_service.deactivate_session(session_id)
    
    def test_format_conversation_for_llm_empty_list(self, chat_service):
        # Act
        result = chat_service.format_conversation_for_llm([])
        
        # Assert
        assert result == []
    
    def test_format_conversation_for_llm_with_messages(self, chat_service, sample_session):
        # Arrange
        messages = [
            Message(
                id=uuid4(),
                session_id=sample_session.id,
                role=MessageRole.USER,
                content="Hello"
            ),
            Message(
                id=uuid4(),
                session_id=sample_session.id,
                role=MessageRole.ASSISTANT,
                content="Hi there!"
            )
        ]
        
        # Act
        result = chat_service.format_conversation_for_llm(messages)
        
        # Assert
        expected = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        assert result == expected
    
    def test_chat_service_initialization_with_custom_limits(
        self, 
        mock_session_repository, 
        mock_message_repository
    ):
        # Act
        service = ChatService(
            session_repository=mock_session_repository,
            message_repository=mock_message_repository,
            max_messages_per_session=200,
            max_daily_messages=100
        )
        
        # Assert
        assert service._max_messages_per_session == 200
        assert service._max_daily_messages == 100
    
    def test_chat_service_initialization_with_defaults(
        self, 
        mock_session_repository, 
        mock_message_repository
    ):
        # Act
        service = ChatService(
            session_repository=mock_session_repository,
            message_repository=mock_message_repository
        )
        
        # Assert
        assert service._max_messages_per_session == 100
        assert service._max_daily_messages == 50
