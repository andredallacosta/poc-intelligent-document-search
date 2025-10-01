import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.chat_session import ChatSession
from domain.entities.message import Message, MessageRole, MessageType, DocumentReference
from domain.exceptions.chat_exceptions import SessionNotFoundError
from domain.value_objects.usuario_id import UsuarioId
from infrastructure.repositories.postgres_session_repository import (
    PostgresSessionRepository,
    PostgresMessageRepository
)
from infrastructure.database.models import ChatSessionModel, MessageModel
from tests.helpers.mock_factories import MockFactory


class TestPostgresSessionRepository:
    
    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def repository(self, mock_session):
        return PostgresSessionRepository(mock_session)
    
    @pytest.fixture
    def sample_chat_session(self):
        return MockFactory.create_chat_session(message_count=2)

    def test_init(self, mock_session):
        repo = PostgresSessionRepository(mock_session)
        assert repo._session == mock_session

    @pytest.mark.asyncio
    async def test_save_session_success(self, repository, mock_session, sample_chat_session):
        mock_session.flush = AsyncMock()
        
        result = await repository.save_session(sample_chat_session)
        
        assert result == sample_chat_session
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_session_integrity_error(self, repository, mock_session, sample_chat_session):
        mock_session.flush.side_effect = IntegrityError("statement", "params", "orig")
        mock_session.rollback = AsyncMock()
        
        with pytest.raises(SessionNotFoundError):
            await repository.save_session(sample_chat_session)
        
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_session_by_id_found(self, repository, mock_session, sample_chat_session):
        mock_model = Mock(spec=ChatSessionModel)
        mock_model.id = sample_chat_session.id
        mock_model.usuario_id = sample_chat_session.usuario_id.value if sample_chat_session.usuario_id else None
        mock_model.ativo = sample_chat_session.is_active
        mock_model.meta_data = sample_chat_session.metadata
        mock_model.criado_em = sample_chat_session.created_at
        mock_model.atualizado_em = sample_chat_session.updated_at
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_chat_session):
            result = await repository.find_session_by_id(sample_chat_session.id)
        
        assert result == sample_chat_session

    @pytest.mark.asyncio
    async def test_find_session_by_id_not_found(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_session_by_id(uuid4())
        
        assert result is None

    @pytest.mark.asyncio
    async def test_find_active_sessions_success(self, repository, mock_session, sample_chat_session):
        mock_model = Mock(spec=ChatSessionModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_chat_session):
            result = await repository.find_active_sessions(limit=10)
        
        assert len(result) == 1
        assert result[0] == sample_chat_session

    @pytest.mark.asyncio
    async def test_find_active_sessions_empty(self, repository, mock_session):
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_active_sessions()
        
        assert result == []

    @pytest.mark.asyncio
    async def test_find_sessions_by_user_success(self, repository, mock_session, sample_chat_session):
        mock_model = Mock(spec=ChatSessionModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_chat_session):
            result = await repository.find_active_sessions(limit=10)
        
        assert len(result) == 1
        assert result[0] == sample_chat_session

    @pytest.mark.asyncio
    async def test_deactivate_session_success(self, repository, mock_session):
        session_id = uuid4()
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        
        result = await repository.deactivate_session(session_id)
        
        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_session_not_found(self, repository, mock_session):
        session_id = uuid4()
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result
        
        result = await repository.deactivate_session(session_id)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_deactivate_session_success(self, repository, mock_session):
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        
        result = await repository.deactivate_session(uuid4())
        
        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_session_not_found(self, repository, mock_session):
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result
        
        result = await repository.deactivate_session(uuid4())
        
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_session_success(self, repository, mock_session):
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        
        result = await repository.delete_session(uuid4())
        
        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_exists_success(self, repository, mock_session):
        session_id = uuid4()
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result
        
        result = await repository.session_exists(session_id)
        
        assert result is True

    def test_model_to_entity(self, repository):
        mock_model = Mock(spec=ChatSessionModel)
        mock_model.id = uuid4()
        mock_model.usuario_id = uuid4()
        mock_model.ativo = True
        mock_model.meta_data = {"key": "value"}
        mock_model.criado_em = datetime.utcnow()
        mock_model.atualizado_em = datetime.utcnow()
        
        result = repository._model_to_entity(mock_model)
        
        assert isinstance(result, ChatSession)
        assert result.id == mock_model.id
        assert result.is_active == mock_model.ativo
        assert result.metadata == mock_model.meta_data


class TestPostgresMessageRepository:
    
    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def repository(self, mock_session):
        return PostgresMessageRepository(mock_session)
    
    @pytest.fixture
    def sample_message(self):
        return MockFactory.create_message()

    def test_init(self, mock_session):
        repo = PostgresMessageRepository(mock_session)
        assert repo._session == mock_session

    @pytest.mark.asyncio
    async def test_save_message_success(self, repository, mock_session, sample_message):
        mock_session.flush = AsyncMock()
        
        result = await repository.save_message(sample_message)
        
        assert result == sample_message
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_message_integrity_error(self, repository, mock_session, sample_message):
        mock_session.flush.side_effect = IntegrityError("statement", "params", "orig")
        mock_session.rollback = AsyncMock()
        
        with pytest.raises(SessionNotFoundError):
            await repository.save_message(sample_message)
        
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_message_by_id_found(self, repository, mock_session, sample_message):
        mock_model = Mock(spec=MessageModel)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_message):
            result = await repository.find_message_by_id(sample_message.id)
        
        assert result == sample_message

    @pytest.mark.asyncio
    async def test_find_message_by_id_not_found(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_message_by_id(uuid4())
        
        assert result is None

    @pytest.mark.asyncio
    async def test_find_messages_by_session_id_success(self, repository, mock_session, sample_message):
        mock_model = Mock(spec=MessageModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_message):
            result = await repository.find_messages_by_session_id(uuid4())
        
        assert len(result) == 1
        assert result[0] == sample_message

    @pytest.mark.asyncio
    async def test_find_messages_by_session_id_empty(self, repository, mock_session):
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_messages_by_session_id(uuid4())
        
        assert result == []

    @pytest.mark.asyncio
    async def test_delete_messages_by_session_id_success(self, repository, mock_session):
        mock_result = Mock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result
        
        result = await repository.delete_messages_by_session_id(uuid4())
        
        assert result == 3
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_messages_by_session_id_success(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 10
        mock_session.execute.return_value = mock_result
        
        result = await repository.count_messages_by_session_id(uuid4())
        
        assert result == 10

    def test_model_to_entity(self, repository):
        mock_model = Mock(spec=MessageModel)
        mock_model.id = uuid4()
        mock_model.session_id = uuid4()
        mock_model.role = MessageRole.USER.value
        mock_model.conteudo = "Test message"
        mock_model.tipo_mensagem = MessageType.TEXT.value
        mock_model.referencias_documento = []
        mock_model.meta_data = {}
        mock_model.criado_em = datetime.utcnow()
        
        result = repository._model_to_entity(mock_model)
        
        assert isinstance(result, Message)
        assert result.id == mock_model.id
        assert result.session_id == mock_model.session_id
        assert result.content == mock_model.conteudo
