from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from domain.entities.chat_session import ChatSession
from domain.entities.message import DocumentReference, Message, MessageRole, MessageType
from domain.exceptions.chat_exceptions import SessionNotFoundError
from domain.repositories.session_repository import MessageRepository, SessionRepository
from infrastructure.config.settings import settings
from infrastructure.external.redis_client import RedisClient


class RedisSessionRepository(SessionRepository):

    def __init__(self, redis_client: RedisClient):
        self._redis_client = redis_client
        self._session_prefix = "session:"
        self._session_ttl = timedelta(seconds=settings.session_ttl_seconds)

    async def save_session(self, session: ChatSession) -> ChatSession:
        try:
            session_data = {
                "id": str(session.id),
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "is_active": session.is_active,
                "metadata": session.metadata,
                "message_count": len(session.messages),
            }

            key = f"{self._session_prefix}{session.id}"
            await self._redis_client.set_json(
                key, session_data, expire=self._session_ttl
            )

            return session
        except Exception as e:
            raise SessionNotFoundError(f"Failed to save session: {e}")

    async def find_session_by_id(self, session_id: UUID) -> Optional[ChatSession]:
        try:
            key = f"{self._session_prefix}{session_id}"
            session_data = await self._redis_client.get_json(key)

            if not session_data:
                return None

            session = ChatSession(
                id=UUID(session_data["id"]),
                messages=[],  # Messages loaded separately
                created_at=datetime.fromisoformat(session_data["created_at"]),
                updated_at=datetime.fromisoformat(session_data["updated_at"]),
                is_active=session_data["is_active"],
                metadata=session_data["metadata"],
            )

            return session
        except Exception:
            return None

    async def find_active_sessions(
        self, limit: Optional[int] = None
    ) -> List[ChatSession]:
        try:
            pattern = f"{self._session_prefix}*"
            session_keys = await self._redis_client.keys_pattern(pattern)

            active_sessions = []

            for key in session_keys[:limit] if limit else session_keys:
                session_data = await self._redis_client.get_json(key)
                if session_data and session_data.get("is_active", True):
                    session = ChatSession(
                        id=UUID(session_data["id"]),
                        messages=[],
                        created_at=datetime.fromisoformat(session_data["created_at"]),
                        updated_at=datetime.fromisoformat(session_data["updated_at"]),
                        is_active=session_data["is_active"],
                        metadata=session_data["metadata"],
                    )
                    active_sessions.append(session)

            return active_sessions
        except Exception:
            return []

    async def delete_session(self, session_id: UUID) -> bool:
        try:
            key = f"{self._session_prefix}{session_id}"
            return await self._redis_client.delete(key)
        except Exception:
            return False

    async def deactivate_session(self, session_id: UUID) -> bool:
        try:
            session = await self.find_session_by_id(session_id)
            if session:
                session.deactivate()
                await self.save_session(session)
                return True
            return False
        except Exception:
            return False

    async def session_exists(self, session_id: UUID) -> bool:
        try:
            key = f"{self._session_prefix}{session_id}"
            return await self._redis_client.exists(key)
        except Exception:
            return False


class RedisMessageRepository(MessageRepository):

    def __init__(self, redis_client: RedisClient):
        self._redis_client = redis_client
        self._message_prefix = "messages:"
        self._message_ttl = timedelta(seconds=settings.session_ttl_seconds)

    async def save_message(self, message: Message) -> Message:
        try:
            message_data = {
                "id": str(message.id),
                "session_id": str(message.session_id),
                "role": message.role.value,
                "content": message.content,
                "message_type": message.message_type.value,
                "document_references": [
                    {
                        "document_id": str(ref.document_id),
                        "chunk_id": str(ref.chunk_id),
                        "source": ref.source,
                        "page": ref.page,
                        "similarity_score": ref.similarity_score,
                        "excerpt": ref.excerpt,
                    }
                    for ref in message.document_references
                ],
                "metadata": message.metadata,
                "created_at": message.created_at.isoformat(),
            }

            # Store message in session's message list
            session_key = f"{self._message_prefix}{message.session_id}"
            await self._redis_client.list_push(session_key, message_data)
            await self._redis_client.expire(
                session_key, self._message_ttl.total_seconds()
            )

            return message
        except Exception as e:
            raise SessionNotFoundError(f"Failed to save message: {e}")

    async def find_message_by_id(self, message_id: UUID) -> Optional[Message]:
        # This would require scanning all sessions - not efficient for Redis
        # In a real implementation, we'd use a separate message index
        return None

    async def find_messages_by_session_id(
        self, session_id: UUID, limit: Optional[int] = None, offset: int = 0
    ) -> List[Message]:
        try:
            session_key = f"{self._message_prefix}{session_id}"

            # Get messages from Redis list (most recent first)
            end_index = offset + limit - 1 if limit else -1
            message_data_list = await self._redis_client.list_get_range(
                session_key, offset, end_index
            )

            messages = []
            for message_data in reversed(
                message_data_list
            ):  # Reverse to get chronological order
                document_references = []
                for ref_data in message_data.get("document_references", []):
                    ref = DocumentReference(
                        document_id=UUID(ref_data["document_id"]),
                        chunk_id=UUID(ref_data["chunk_id"]),
                        source=ref_data["source"],
                        page=ref_data.get("page"),
                        similarity_score=ref_data.get("similarity_score"),
                        excerpt=ref_data.get("excerpt"),
                    )
                    document_references.append(ref)

                message = Message(
                    id=UUID(message_data["id"]),
                    session_id=UUID(message_data["session_id"]),
                    role=MessageRole(message_data["role"]),
                    content=message_data["content"],
                    message_type=MessageType(message_data["message_type"]),
                    document_references=document_references,
                    metadata=message_data["metadata"],
                    created_at=datetime.fromisoformat(message_data["created_at"]),
                )
                messages.append(message)

            return messages
        except Exception:
            return []

    async def delete_messages_by_session_id(self, session_id: UUID) -> int:
        try:
            session_key = f"{self._message_prefix}{session_id}"
            count = await self._redis_client.list_length(session_key)
            await self._redis_client.delete(session_key)
            return count
        except Exception:
            return 0

    async def count_messages_by_session_id(self, session_id: UUID) -> int:
        try:
            session_key = f"{self._message_prefix}{session_id}"
            return await self._redis_client.list_length(session_key)
        except Exception:
            return 0
