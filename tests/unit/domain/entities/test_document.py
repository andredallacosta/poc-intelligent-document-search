from datetime import datetime
from uuid import uuid4

from domain.entities.document import Document, DocumentChunk


class TestDocumentChunk:
    def test_create_document_chunk(self, sample_embedding):
        chunk = DocumentChunk(
            id=uuid4(),
            document_id=uuid4(),
            content="Test content",
            original_content="Test content",
            chunk_index=0,
            start_char=0,
            end_char=12,
            embedding=sample_embedding,
        )
        assert chunk.content == "Test content"
        assert chunk.chunk_index == 0
        assert chunk.embedding == sample_embedding
        assert isinstance(chunk.created_at, datetime)

    def test_document_chunk_without_embedding(self):
        chunk = DocumentChunk(
            id=uuid4(),
            document_id=uuid4(),
            content="Test content",
            original_content="Test content",
            chunk_index=0,
            start_char=0,
            end_char=12,
        )
        assert chunk.embedding is None
        assert chunk.content == "Test content"


class TestDocument:
    def test_create_document(self, sample_document_metadata):
        doc = Document(
            id=uuid4(),
            title="Test Document",
            content="Test content",
            file_path="/test/doc.pdf",
            metadata=sample_document_metadata,
            chunks=[],
        )
        assert doc.title == "Test Document"
        assert doc.content == "Test content"
        assert doc.chunk_count == 0
        assert doc.word_count == 2
        assert isinstance(doc.created_at, datetime)
        assert isinstance(doc.updated_at, datetime)

    def test_add_chunk_to_document(self, sample_document, sample_document_chunk):
        initial_count = sample_document.chunk_count
        initial_updated_at = sample_document.updated_at
        new_chunk = DocumentChunk(
            id=uuid4(),
            document_id=uuid4(),
            content="New chunk",
            original_content="New chunk",
            chunk_index=1,
            start_char=100,
            end_char=109,
        )
        sample_document.add_chunk(new_chunk)
        assert sample_document.chunk_count == initial_count + 1
        assert new_chunk.document_id == sample_document.id
        assert sample_document.updated_at > initial_updated_at

    def test_get_chunk_by_index(self, sample_document):
        chunk = sample_document.get_chunk_by_index(0)
        assert chunk is not None
        assert chunk.chunk_index == 0

    def test_get_nonexistent_chunk_by_index(self, sample_document):
        chunk = sample_document.get_chunk_by_index(999)
        assert chunk is None

    def test_word_count_calculation(self, sample_document_metadata):
        doc = Document(
            id=uuid4(),
            title="Test",
            content="This is a test document with multiple words",
            file_path="/test.pdf",
            metadata=sample_document_metadata,
            chunks=[],
        )
        assert doc.word_count == 8

    def test_document_auto_generates_id_and_timestamps(self, sample_document_metadata):
        doc = Document(
            id=None,
            title="Test",
            content="Test",
            file_path="/test.pdf",
            metadata=sample_document_metadata,
            chunks=[],
        )
        assert doc.id is not None
        assert doc.created_at is not None
        assert doc.updated_at is not None
