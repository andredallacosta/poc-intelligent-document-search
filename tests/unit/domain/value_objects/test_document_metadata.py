import pytest
from datetime import datetime

from domain.value_objects.document_metadata import DocumentMetadata

class TestDocumentMetadata:
    
    def test_create_minimal_metadata(self):
        metadata = DocumentMetadata(
            source="test.pdf",
            file_size=1024,
            file_type="pdf"
        )
        
        assert metadata.source == "test.pdf"
        assert metadata.file_size == 1024
        assert metadata.file_type == "pdf"
        assert metadata.custom_fields == {}
    
    def test_create_complete_metadata(self):
        creation_date = datetime(2023, 1, 1, 12, 0, 0)
        modification_date = datetime(2023, 1, 2, 12, 0, 0)
        custom_fields = {"department": "IT", "priority": "high"}
        
        metadata = DocumentMetadata(
            source="document.docx",
            file_size=2048,
            file_type="docx",
            page_count=10,
            word_count=500,
            language="en",
            author="John Doe",
            title="Test Document",
            subject="Testing",
            creation_date=creation_date,
            modification_date=modification_date,
            custom_fields=custom_fields
        )
        
        assert metadata.source == "document.docx"
        assert metadata.file_size == 2048
        assert metadata.file_type == "docx"
        assert metadata.page_count == 10
        assert metadata.word_count == 500
        assert metadata.language == "en"
        assert metadata.author == "John Doe"
        assert metadata.title == "Test Document"
        assert metadata.subject == "Testing"
        assert metadata.creation_date == creation_date
        assert metadata.modification_date == modification_date
        assert metadata.custom_fields == custom_fields
    
    def test_custom_fields_default_initialization(self):
        metadata = DocumentMetadata(
            source="test.pdf",
            file_size=1024,
            file_type="pdf"
        )
        
        assert metadata.custom_fields == {}
    
    def test_is_pdf_property(self):
        pdf_metadata = DocumentMetadata(
            source="test.pdf",
            file_size=1024,
            file_type="PDF"
        )
        
        non_pdf_metadata = DocumentMetadata(
            source="test.docx",
            file_size=1024,
            file_type="docx"
        )
        
        assert pdf_metadata.is_pdf is True
        assert non_pdf_metadata.is_pdf is False
    
    def test_is_docx_property(self):
        docx_metadata = DocumentMetadata(
            source="test.docx",
            file_size=1024,
            file_type="DOCX"
        )
        
        doc_metadata = DocumentMetadata(
            source="test.doc",
            file_size=1024,
            file_type="doc"
        )
        
        pdf_metadata = DocumentMetadata(
            source="test.pdf",
            file_size=1024,
            file_type="pdf"
        )
        
        assert docx_metadata.is_docx is True
        assert doc_metadata.is_docx is True
        assert pdf_metadata.is_docx is False
    
    def test_is_web_content_property(self):
        html_metadata = DocumentMetadata(
            source="webpage.html",
            file_size=1024,
            file_type="HTML"
        )
        
        pdf_metadata = DocumentMetadata(
            source="test.pdf",
            file_size=1024,
            file_type="pdf"
        )
        
        assert html_metadata.is_web_content is True
        assert pdf_metadata.is_web_content is False
    
    def test_size_mb_property(self):
        metadata = DocumentMetadata(
            source="test.pdf",
            file_size=1024 * 1024,
            file_type="pdf"
        )
        
        assert metadata.size_mb == 1.0
        
        small_metadata = DocumentMetadata(
            source="small.txt",
            file_size=512 * 1024,
            file_type="txt"
        )
        
        assert small_metadata.size_mb == 0.5
    
    def test_get_custom_field_existing(self):
        metadata = DocumentMetadata(
            source="test.pdf",
            file_size=1024,
            file_type="pdf",
            custom_fields={"department": "IT", "priority": "high"}
        )
        
        assert metadata.get_custom_field("department") == "IT"
        assert metadata.get_custom_field("priority") == "high"
    
    def test_get_custom_field_nonexistent(self):
        metadata = DocumentMetadata(
            source="test.pdf",
            file_size=1024,
            file_type="pdf",
            custom_fields={"department": "IT"}
        )
        
        assert metadata.get_custom_field("nonexistent") is None
        assert metadata.get_custom_field("nonexistent", "default") == "default"
    
    def test_with_custom_field_new_field(self):
        original = DocumentMetadata(
            source="test.pdf",
            file_size=1024,
            file_type="pdf",
            custom_fields={"existing": "value"}
        )
        
        updated = original.with_custom_field("new_field", "new_value")
        
        assert original.custom_fields == {"existing": "value"}
        
        assert updated.custom_fields == {"existing": "value", "new_field": "new_value"}
        
        assert updated.source == original.source
        assert updated.file_size == original.file_size
        assert updated.file_type == original.file_type
    
    def test_with_custom_field_update_existing(self):
        original = DocumentMetadata(
            source="test.pdf",
            file_size=1024,
            file_type="pdf",
            custom_fields={"field": "old_value"}
        )
        
        updated = original.with_custom_field("field", "new_value")
        
        assert original.custom_fields == {"field": "old_value"}
        
        assert updated.custom_fields == {"field": "new_value"}
    
    def test_metadata_is_frozen(self):
        metadata = DocumentMetadata(
            source="test.pdf",
            file_size=1024,
            file_type="pdf"
        )
        
        with pytest.raises(AttributeError):
            metadata.source = "new_source.pdf"
    
    def test_metadata_equality(self):
        metadata1 = DocumentMetadata(
            source="test.pdf",
            file_size=1024,
            file_type="pdf",
            custom_fields={"key": "value"}
        )
        
        metadata2 = DocumentMetadata(
            source="test.pdf",
            file_size=1024,
            file_type="pdf",
            custom_fields={"key": "value"}
        )
        
        metadata3 = DocumentMetadata(
            source="different.pdf",
            file_size=1024,
            file_type="pdf",
            custom_fields={"key": "value"}
        )
        
        assert metadata1 == metadata2
        assert metadata1 != metadata3
    
    def test_metadata_hash(self):
        metadata1 = DocumentMetadata(
            source="test.pdf",
            file_size=1024,
            file_type="pdf"
        )
        
        metadata2 = DocumentMetadata(
            source="test.pdf",
            file_size=1024,
            file_type="pdf"
        )
        
        assert hash(metadata1) == hash(metadata2)
        
        metadata_set = {metadata1, metadata2}
        assert len(metadata_set) == 1
