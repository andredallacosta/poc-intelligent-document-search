import pytest
import asyncio
import sys
import os
from datetime import datetime
from uuid import uuid4
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from domain.entities.document import Document, DocumentChunk
from domain.entities.chat_session import ChatSession
from domain.entities.message import Message, MessageRole, DocumentReference
from domain.value_objects.document_metadata import DocumentMetadata
from domain.value_objects.embedding import Embedding
from tests.helpers.mock_factories import MockFactory, MockServiceFactory

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def sample_embedding() -> Embedding:
    return MockFactory.create_embedding()

@pytest.fixture
def sample_document_metadata() -> DocumentMetadata:
    return MockFactory.create_document_metadata()

@pytest.fixture
def sample_document_chunk(sample_embedding: Embedding) -> DocumentChunk:
    return MockFactory.create_document_chunk(with_embedding=True)

@pytest.fixture
def sample_document(sample_document_metadata: DocumentMetadata) -> Document:
    return MockFactory.create_document(chunk_count=2)

@pytest.fixture
def sample_message() -> Message:
    return MockFactory.create_message()

@pytest.fixture
def sample_chat_session() -> ChatSession:
    return MockFactory.create_chat_session(message_count=2)

@pytest.fixture
def sample_document_reference() -> DocumentReference:
    return MockFactory.create_document_reference()

@pytest.fixture
def mock_data_factory() -> MockFactory:
    return MockFactory()

@pytest.fixture
def mock_service_factory() -> MockServiceFactory:
    return MockServiceFactory()

@pytest.fixture
def mock_chat_service():
    return MockServiceFactory.create_mock_chat_service()

@pytest.fixture
def mock_search_service():
    return MockServiceFactory.create_mock_search_service()

@pytest.fixture
def mock_llm_service():
    return MockServiceFactory.create_mock_llm_service()

@pytest.fixture
def mock_vector_repository():
    return MockServiceFactory.create_mock_vector_repository()

@pytest.fixture
def mock_session_repository():
    return MockServiceFactory.create_mock_session_repository()

@pytest.fixture
def sample_search_results(mock_data_factory):
    return mock_data_factory.create_search_results(3)

@pytest.fixture
def sample_conversation_history():
    messages = []
    for i in range(4):
        role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
        message = MockFactory.create_message(
            role=role,
            content=f"Message {i} in conversation"
        )
        messages.append(message)
    return messages
