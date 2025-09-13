import pytest
from datetime import datetime
from uuid import uuid4

from domain.entities.message import Message, MessageRole, MessageType, DocumentReference


class TestDocumentReference:
    
    def test_create_document_reference_minimal(self):
        ref = DocumentReference(
            document_id=uuid4(),
            chunk_id=uuid4(),
            source="test.pdf"
        )
        
        assert ref.page is None
        assert ref.similarity_score is None
        assert ref.excerpt is None
    
    def test_create_document_reference_complete(self):
        doc_id = uuid4()
        chunk_id = uuid4()
        
        ref = DocumentReference(
            document_id=doc_id,
            chunk_id=chunk_id,
            source="test.pdf",
            page=5,
            similarity_score=0.85,
            excerpt="Test excerpt"
        )
        
        assert ref.document_id == doc_id
        assert ref.chunk_id == chunk_id
        assert ref.source == "test.pdf"
        assert ref.page == 5
        assert ref.similarity_score == 0.85
        assert ref.excerpt == "Test excerpt"


class TestMessage:
    
    def test_create_message_minimal(self):
        message = Message(
            id=uuid4(),
            session_id=uuid4(),
            role=MessageRole.USER,
            content="Hello world"
        )
        
        assert message.message_type == MessageType.TEXT
        assert message.document_references == []
        assert message.metadata == {}
        assert isinstance(message.created_at, datetime)
    
    def test_create_message_with_all_fields(self):
        msg_id = uuid4()
        session_id = uuid4()
        references = [DocumentReference(
            document_id=uuid4(),
            chunk_id=uuid4(),
            source="test.pdf"
        )]
        metadata = {"test": True}
        
        message = Message(
            id=msg_id,
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content="Response content",
            message_type=MessageType.SEARCH_RESULT,
            document_references=references,
            metadata=metadata
        )
        
        assert message.id == msg_id
        assert message.session_id == session_id
        assert message.role == MessageRole.ASSISTANT
        assert message.content == "Response content"
        assert message.message_type == MessageType.SEARCH_RESULT
        assert message.document_references == references
        assert message.metadata == metadata
    
    def test_message_auto_generates_id_and_timestamp(self):
        message = Message(
            id=None,
            session_id=uuid4(),
            role=MessageRole.USER,
            content="Test"
        )
        
        assert message.id is not None
        assert message.created_at is not None
    
    def test_has_references_property(self):
        # Message without references
        message = Message(
            id=uuid4(),
            session_id=uuid4(),
            role=MessageRole.USER,
            content="Test"
        )
        
        assert message.has_references is False
        assert message.reference_count == 0
        
        # Add reference
        ref = DocumentReference(
            document_id=uuid4(),
            chunk_id=uuid4(),
            source="test.pdf"
        )
        message.add_document_reference(ref)
        
        assert message.has_references is True
        assert message.reference_count == 1
    
    def test_add_document_reference(self):
        message = Message(
            id=uuid4(),
            session_id=uuid4(),
            role=MessageRole.ASSISTANT,
            content="Response"
        )
        
        ref1 = DocumentReference(
            document_id=uuid4(),
            chunk_id=uuid4(),
            source="doc1.pdf"
        )
        ref2 = DocumentReference(
            document_id=uuid4(),
            chunk_id=uuid4(),
            source="doc2.pdf"
        )
        
        message.add_document_reference(ref1)
        message.add_document_reference(ref2)
        
        assert message.reference_count == 2
        assert ref1 in message.document_references
        assert ref2 in message.document_references
    
    def test_get_references_by_source(self):
        message = Message(
            id=uuid4(),
            session_id=uuid4(),
            role=MessageRole.ASSISTANT,
            content="Response"
        )
        
        ref1 = DocumentReference(
            document_id=uuid4(),
            chunk_id=uuid4(),
            source="doc1.pdf"
        )
        ref2 = DocumentReference(
            document_id=uuid4(),
            chunk_id=uuid4(),
            source="doc2.pdf"
        )
        ref3 = DocumentReference(
            document_id=uuid4(),
            chunk_id=uuid4(),
            source="doc1.pdf"  # Same source as ref1
        )
        
        message.add_document_reference(ref1)
        message.add_document_reference(ref2)
        message.add_document_reference(ref3)
        
        doc1_refs = message.get_references_by_source("doc1.pdf")
        doc2_refs = message.get_references_by_source("doc2.pdf")
        nonexistent_refs = message.get_references_by_source("nonexistent.pdf")
        
        assert len(doc1_refs) == 2
        assert len(doc2_refs) == 1
        assert len(nonexistent_refs) == 0
        assert ref1 in doc1_refs
        assert ref3 in doc1_refs
        assert ref2 in doc2_refs
    
    def test_message_types_enum(self):
        # Test all message types
        text_msg = Message(
            id=uuid4(),
            session_id=uuid4(),
            role=MessageRole.USER,
            content="Text message",
            message_type=MessageType.TEXT
        )
        
        search_msg = Message(
            id=uuid4(),
            session_id=uuid4(),
            role=MessageRole.ASSISTANT,
            content="Search result",
            message_type=MessageType.SEARCH_RESULT
        )
        
        error_msg = Message(
            id=uuid4(),
            session_id=uuid4(),
            role=MessageRole.SYSTEM,
            content="Error occurred",
            message_type=MessageType.ERROR
        )
        
        assert text_msg.message_type == MessageType.TEXT
        assert search_msg.message_type == MessageType.SEARCH_RESULT
        assert error_msg.message_type == MessageType.ERROR
    
    def test_message_roles_enum(self):
        # Test all message roles
        user_msg = Message(
            id=uuid4(),
            session_id=uuid4(),
            role=MessageRole.USER,
            content="User message"
        )
        
        assistant_msg = Message(
            id=uuid4(),
            session_id=uuid4(),
            role=MessageRole.ASSISTANT,
            content="Assistant response"
        )
        
        system_msg = Message(
            id=uuid4(),
            session_id=uuid4(),
            role=MessageRole.SYSTEM,
            content="System message"
        )
        
        assert user_msg.role == MessageRole.USER
        assert assistant_msg.role == MessageRole.ASSISTANT
        assert system_msg.role == MessageRole.SYSTEM
