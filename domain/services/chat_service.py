from typing import List, Optional
from uuid import UUID, uuid4

from domain.entities.chat_session import ChatSession
from domain.entities.message import DocumentReference, Message, MessageRole, MessageType
from domain.exceptions.chat_exceptions import (
    InvalidMessageError,
    RateLimitExceededError,
    SessionNotFoundError,
)
from domain.repositories.session_repository import MessageRepository, SessionRepository


class ChatService:

    def __init__(
        self,
        session_repository: SessionRepository,
        message_repository: MessageRepository,
        max_messages_per_session: int = 100,
        max_daily_messages: int = 50,
    ):
        self._session_repository = session_repository
        self._message_repository = message_repository
        self._max_messages_per_session = max_messages_per_session
        self._max_daily_messages = max_daily_messages

    async def create_session(self) -> ChatSession:
        session = ChatSession(id=uuid4())
        return await self._session_repository.save_session(session)

    async def get_session(self, session_id: UUID) -> ChatSession:
        session = await self._session_repository.find_session_by_id(session_id)
        if not session:
            raise SessionNotFoundError(f"Session '{session_id}' not found")
        return session

    async def add_user_message(
        self, session_id: UUID, content: str, metadata: dict = None
    ) -> Message:
        if not content.strip():
            raise InvalidMessageError("Message content cannot be empty")

        session = await self.get_session(session_id)

        await self._check_rate_limits(session)

        message = Message(
            id=uuid4(),
            session_id=session_id,
            role=MessageRole.USER,
            content=content.strip(),
            message_type=MessageType.TEXT,
            metadata=metadata or {},
        )

        session.add_message(message)
        await self._session_repository.save_session(session)
        await self._message_repository.save_message(message)

        return message

    async def add_assistant_message(
        self,
        session_id: UUID,
        content: str,
        document_references: List[DocumentReference] = None,
        metadata: dict = None,
    ) -> Message:
        if not content.strip():
            raise InvalidMessageError("Message content cannot be empty")

        session = await self.get_session(session_id)

        message = Message(
            id=uuid4(),
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=content.strip(),
            message_type=MessageType.TEXT,
            document_references=document_references or [],
            metadata=metadata or {},
        )

        session.add_message(message)
        await self._session_repository.save_session(session)
        await self._message_repository.save_message(message)

        return message

    async def get_conversation_history(
        self, session_id: UUID, limit: Optional[int] = None
    ) -> List[Message]:
        await self.get_session(session_id)
        return await self._message_repository.find_messages_by_session_id(
            session_id, limit=limit
        )

    async def deactivate_session(self, session_id: UUID) -> bool:
        session = await self.get_session(session_id)
        session.deactivate()
        await self._session_repository.save_session(session)
        return True

    async def _check_rate_limits(self, session: ChatSession) -> None:
        if session.message_count >= self._max_messages_per_session:
            raise RateLimitExceededError(
                f"Session has reached maximum of {self._max_messages_per_session} messages"
            )

    def format_conversation_for_llm(self, messages: List[Message]) -> List[dict]:
        formatted_messages = []

        for message in messages:
            formatted_messages.append(
                {"role": message.role.value, "content": message.content}
            )

        return formatted_messages
