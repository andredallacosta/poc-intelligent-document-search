import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from datetime import datetime, timedelta
import json

from domain.entities.chat_session import ChatSession
from domain.entities.message import Message, MessageRole, DocumentReference
from domain.exceptions.chat_exceptions import SessionNotFoundError
from domain.value_objects.user_id import UserId
from infrastructure.repositories.redis_session_repository import (
    RedisSessionRepository,
    RedisMessageRepository
)
from infrastructure.external.redis_client import RedisClient
from tests.helpers.mock_factories import MockFactory


class TestRedisSessionRepository:
    
    @pytest.fixture
    def mock_redis_client(self):
        return AsyncMock(spec=RedisClient)
    
    @pytest.fixture
    def repository(self, mock_redis_client):
        return RedisSessionRepository(mock_redis_client)
    
    @pytest.fixture
    def sample_chat_session(self):
        return MockFactory.create_chat_session(message_count=2)

    def test_init(self, mock_redis_client):
        repo = RedisSessionRepository(mock_redis_client)
        assert repo._redis_client == mock_redis_client
        assert repo._session_prefix == "session:"

    @pytest.mark.asyncio
    async def test_save_session_success(self, repository, mock_redis_client, sample_chat_session):
        mock_redis_client.set_json = AsyncMock()
        
        result = await repository.save_session(sample_chat_session)
        
        assert result == sample_chat_session
        mock_redis_client.set_json.assert_called_once()
        
        # Verify the data structure passed to Redis
        call_args = mock_redis_client.set_json.call_args
        key, data, expire = call_args[0][0], call_args[0][1], call_args[1]['expire']
        
        assert key == f"session:{sample_chat_session.id}"
        assert data["id"] == str(sample_chat_session.id)
        assert data["is_active"] == sample_chat_session.is_active
        assert isinstance(expire, timedelta)

    @pytest.mark.asyncio
    async def test_save_session_redis_error(self, repository, mock_redis_client, sample_chat_session):
        mock_redis_client.set_json.side_effect = Exception("Redis connection error")
        
        with pytest.raises(SessionNotFoundError, match="Failed to save session"):
            await repository.save_session(sample_chat_session)

    @pytest.mark.asyncio
    async def test_find_session_by_id_found(self, repository, mock_redis_client, sample_chat_session):
        session_data = {
            "id": str(sample_chat_session.id),
            "created_at": sample_chat_session.created_at.isoformat(),
            "updated_at": sample_chat_session.updated_at.isoformat(),
            "is_active": sample_chat_session.is_active,
            "metadata": sample_chat_session.metadata,
            "message_count": len(sample_chat_session.messages)
        }
        
        mock_redis_client.get_json.return_value = session_data
        
        result = await repository.find_session_by_id(sample_chat_session.id)
        
        assert result is not None
        assert result.id == sample_chat_session.id
        assert result.is_active == sample_chat_session.is_active
        mock_redis_client.get_json.assert_called_once_with(f"session:{sample_chat_session.id}")

    @pytest.mark.asyncio
    async def test_find_session_by_id_not_found(self, repository, mock_redis_client):
        mock_redis_client.get_json.return_value = None
        
        result = await repository.find_session_by_id(uuid4())
        
        assert result is None

    @pytest.mark.asyncio
    async def test_find_session_by_id_redis_error_handled(self, repository, mock_redis_client):
        mock_redis_client.get_json.side_effect = Exception("Redis connection error")
        
        # O método captura a exceção e retorna None
        result = await repository.find_session_by_id(uuid4())
        
        assert result is None

    @pytest.mark.asyncio
    async def test_find_active_sessions_success(self, repository, mock_redis_client, sample_chat_session):
        # Mock Redis keys_pattern operation
        session_keys = [f"session:{sample_chat_session.id}"]
        session_data = {
            "id": str(sample_chat_session.id),
            "created_at": sample_chat_session.created_at.isoformat(),
            "updated_at": sample_chat_session.updated_at.isoformat(),
            "is_active": True,
            "metadata": sample_chat_session.metadata,
            "message_count": 2
        }
        
        mock_redis_client.keys_pattern.return_value = session_keys
        mock_redis_client.get_json.return_value = session_data
        
        result = await repository.find_active_sessions(limit=10)
        
        assert len(result) == 1
        assert result[0].id == sample_chat_session.id
        assert result[0].is_active is True

    @pytest.mark.asyncio
    async def test_find_active_sessions_empty(self, repository, mock_redis_client):
        mock_redis_client.keys_pattern.return_value = []
        
        result = await repository.find_active_sessions()
        
        assert result == []

    @pytest.mark.asyncio
    async def test_session_exists_true(self, repository, mock_redis_client):
        session_id = uuid4()
        mock_redis_client.exists.return_value = True
        
        result = await repository.session_exists(session_id)
        
        assert result is True
        mock_redis_client.exists.assert_called_once_with(f"session:{session_id}")

    @pytest.mark.asyncio
    async def test_session_exists_false(self, repository, mock_redis_client):
        session_id = uuid4()
        mock_redis_client.exists.return_value = False
        
        result = await repository.session_exists(session_id)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_find_session_by_id_redis_error_handled(self, repository, mock_redis_client):
        mock_redis_client.get_json.side_effect = Exception("Redis connection error")
        
        # O método captura a exceção e retorna None
        result = await repository.find_session_by_id(uuid4())
        
        assert result is None

    @pytest.mark.asyncio
    async def test_deactivate_session_success(self, repository, mock_redis_client):
        session_id = uuid4()
        existing_data = {
            "id": str(session_id),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "is_active": True,
            "metadata": {},
            "message_count": 1
        }
        
        mock_redis_client.get_json.return_value = existing_data
        mock_redis_client.set_json = AsyncMock()
        
        result = await repository.deactivate_session(session_id)
        
        assert result is True
        mock_redis_client.set_json.assert_called_once()
        
        # Verify session was marked as inactive
        call_args = mock_redis_client.set_json.call_args
        updated_data = call_args[0][1]
        assert updated_data["is_active"] is False

    @pytest.mark.asyncio
    async def test_deactivate_session_not_found(self, repository, mock_redis_client):
        mock_redis_client.get_json.return_value = None
        
        result = await repository.deactivate_session(uuid4())
        
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_session_success(self, repository, mock_redis_client):
        session_id = uuid4()
        mock_redis_client.delete.return_value = 1  # 1 key deleted
        
        result = await repository.delete_session(session_id)
        
        assert result is True
        mock_redis_client.delete.assert_called_once_with(f"session:{session_id}")

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, repository, mock_redis_client):
        session_id = uuid4()
        mock_redis_client.delete.return_value = 0  # No keys deleted
        
        result = await repository.delete_session(session_id)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_session_success(self, repository, mock_redis_client):
        session_id = uuid4()
        mock_redis_client.delete.return_value = True
        
        result = await repository.delete_session(session_id)
        
        assert result is True
        mock_redis_client.delete.assert_called_once_with(f"session:{session_id}")

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, repository, mock_redis_client):
        session_id = uuid4()
        mock_redis_client.delete.return_value = False
        
        result = await repository.delete_session(session_id)
        
        assert result is False


class TestRedisMessageRepository:
    
    @pytest.fixture
    def mock_redis_client(self):
        return AsyncMock(spec=RedisClient)
    
    @pytest.fixture
    def repository(self, mock_redis_client):
        return RedisMessageRepository(mock_redis_client)
    
    @pytest.fixture
    def sample_message(self):
        return MockFactory.create_message()

    def test_init(self, mock_redis_client):
        repo = RedisMessageRepository(mock_redis_client)
        assert repo._redis_client == mock_redis_client
        assert repo._message_prefix == "messages:"

    @pytest.mark.asyncio
    async def test_save_message_success(self, repository, mock_redis_client, sample_message):
        mock_redis_client.list_push = AsyncMock()
        mock_redis_client.expire = AsyncMock()
        
        result = await repository.save_message(sample_message)
        
        assert result == sample_message
        mock_redis_client.list_push.assert_called_once()
        mock_redis_client.expire.assert_called_once()
        
        # Verify the data structure
        call_args = mock_redis_client.list_push.call_args
        key, data = call_args[0][0], call_args[0][1]
        
        assert key == f"messages:{sample_message.session_id}"
        assert data["id"] == str(sample_message.id)
        assert data["session_id"] == str(sample_message.session_id)
        assert data["role"] == sample_message.role.value
        assert data["content"] == sample_message.content

    @pytest.mark.asyncio
    async def test_save_message_redis_error(self, repository, mock_redis_client, sample_message):
        mock_redis_client.list_push.side_effect = Exception("Redis connection error")
        
        with pytest.raises(SessionNotFoundError, match="Failed to save message"):
            await repository.save_message(sample_message)

    @pytest.mark.asyncio
    async def test_find_message_by_id_not_implemented(self, repository):
        # O método find_message_by_id sempre retorna None (não implementado)
        result = await repository.find_message_by_id(uuid4())
        
        assert result is None

    @pytest.mark.asyncio
    async def test_find_messages_by_session_id_success(self, repository, mock_redis_client, sample_message):
        session_id = uuid4()
        message_data = {
            "id": str(sample_message.id),
            "session_id": str(session_id),
            "role": sample_message.role.value,
            "content": sample_message.content,
            "message_type": sample_message.message_type.value,
            "document_references": [],
            "metadata": {},
            "created_at": sample_message.created_at.isoformat()
        }
        
        mock_redis_client.list_get_range.return_value = [message_data]
        
        result = await repository.find_messages_by_session_id(session_id)
        
        assert len(result) == 1
        assert result[0].id == sample_message.id
        assert result[0].session_id == session_id

    @pytest.mark.asyncio
    async def test_find_messages_by_session_id_empty(self, repository, mock_redis_client):
        mock_redis_client.list_get_range.return_value = []
        
        result = await repository.find_messages_by_session_id(uuid4())
        
        assert result == []

    @pytest.mark.asyncio
    async def test_delete_messages_by_session_id_success(self, repository, mock_redis_client):
        session_id = uuid4()
        
        mock_redis_client.list_length.return_value = 3
        mock_redis_client.delete = AsyncMock()
        
        result = await repository.delete_messages_by_session_id(session_id)
        
        assert result == 3
        mock_redis_client.delete.assert_called_once_with(f"messages:{session_id}")

    @pytest.mark.asyncio
    async def test_delete_messages_by_session_id_no_messages(self, repository, mock_redis_client):
        session_id = uuid4()
        
        mock_redis_client.list_length.return_value = 0
        mock_redis_client.delete = AsyncMock()
        
        result = await repository.delete_messages_by_session_id(session_id)
        
        assert result == 0

    @pytest.mark.asyncio
    async def test_count_messages_by_session_id_success(self, repository, mock_redis_client):
        session_id = uuid4()
        
        mock_redis_client.list_length.return_value = 2
        
        result = await repository.count_messages_by_session_id(session_id)
        
        assert result == 2

    @pytest.mark.asyncio
    async def test_count_messages_by_session_id_empty(self, repository, mock_redis_client):
        session_id = uuid4()
        
        mock_redis_client.list_length.return_value = 0
        
        result = await repository.count_messages_by_session_id(session_id)
        
        assert result == 0
