import pytest
from datetime import datetime
from uuid import uuid4

from domain.entities.chat_session import ChatSession
from domain.entities.message import Message, MessageRole


class TestChatSession:
    
    def test_create_empty_chat_session(self):
        session = ChatSession(id=uuid4())
        
        assert session.message_count == 0
        assert session.last_message is None
        assert session.is_active is True
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)
        assert isinstance(session.metadata, dict)
    
    def test_add_message_to_session(self):
        session = ChatSession(id=uuid4())
        message = Message(
            id=uuid4(),
            session_id=uuid4(),
            role=MessageRole.USER,
            content="Hello, world!",
            document_references=[],
            metadata={}
        )
        
        initial_updated_at = session.updated_at
        session.add_message(message)
        
        assert session.message_count == 1
        assert session.last_message == message
        assert message.session_id == session.id
        assert session.updated_at > initial_updated_at
    
    def test_add_multiple_messages(self):
        session = ChatSession(id=uuid4())
        
        messages = []
        for i in range(3):
            message = Message(
                id=uuid4(),
                session_id=uuid4(),
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"Message {i}",
                document_references=[],
                metadata={}
            )
            messages.append(message)
            session.add_message(message)
        
        assert session.message_count == 3
        assert session.last_message == messages[-1]
        
        # All messages should have the session ID updated
        for message in session.messages:
            assert message.session_id == session.id
    
    def test_get_conversation_history_no_limit(self):
        session = ChatSession(id=uuid4())
        
        # Add messages with different timestamps
        for i in range(5):
            message = Message(
                id=uuid4(),
                session_id=session.id,
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"Message {i}",
                document_references=[],
                metadata={}
            )
            session.add_message(message)
        
        history = session.get_conversation_history()
        
        assert len(history) == 5
        # Should be sorted by created_at
        for i in range(1, len(history)):
            assert history[i].created_at >= history[i-1].created_at
    
    def test_get_conversation_history_with_limit(self):
        session = ChatSession(id=uuid4())
        
        # Add 5 messages
        for i in range(5):
            message = Message(
                id=uuid4(),
                session_id=session.id,
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"Message {i}",
                document_references=[],
                metadata={}
            )
            session.add_message(message)
        
        history = session.get_conversation_history(limit=3)
        
        assert len(history) == 3
        # Should return the last 3 messages
        assert history[0].content == "Message 2"
        assert history[1].content == "Message 3"
        assert history[2].content == "Message 4"
    
    def test_deactivate_session(self):
        session = ChatSession(id=uuid4())
        initial_updated_at = session.updated_at
        
        assert session.is_active is True
        
        session.deactivate()
        
        assert session.is_active is False
        assert session.updated_at > initial_updated_at
    
    def test_session_auto_generates_id_and_timestamps(self):
        session = ChatSession(id=None)
        
        assert session.id is not None
        assert session.created_at is not None
        assert session.updated_at is not None
    
    def test_empty_session_last_message(self):
        session = ChatSession(id=uuid4())
        
        assert session.last_message is None
        assert session.message_count == 0
