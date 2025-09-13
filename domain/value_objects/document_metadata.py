from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass(frozen=True)
class DocumentMetadata:
    source: str
    file_size: int
    file_type: str
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    language: Optional[str] = None
    author: Optional[str] = None
    title: Optional[str] = None
    subject: Optional[str] = None
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    custom_fields: Dict = field(default_factory=dict)
    
    def __hash__(self):
        # Custom hash implementation that excludes mutable custom_fields
        return hash((
            self.source,
            self.file_size,
            self.file_type,
            self.page_count,
            self.word_count,
            self.language,
            self.author,
            self.title,
            self.subject,
            self.creation_date,
            self.modification_date,
            tuple(sorted(self.custom_fields.items())) if self.custom_fields else ()
        ))
    
    @property
    def is_pdf(self) -> bool:
        return self.file_type.lower() == 'pdf'
    
    @property
    def is_docx(self) -> bool:
        return self.file_type.lower() in ['docx', 'doc']
    
    @property
    def is_web_content(self) -> bool:
        return self.file_type.lower() == 'html'
    
    @property
    def size_mb(self) -> float:
        return self.file_size / (1024 * 1024)
    
    def get_custom_field(self, key: str, default=None):
        return self.custom_fields.get(key, default)
    
    def with_custom_field(self, key: str, value) -> 'DocumentMetadata':
        new_custom_fields = {**self.custom_fields, key: value}
        return DocumentMetadata(
            source=self.source,
            file_size=self.file_size,
            file_type=self.file_type,
            page_count=self.page_count,
            word_count=self.word_count,
            language=self.language,
            author=self.author,
            title=self.title,
            subject=self.subject,
            creation_date=self.creation_date,
            modification_date=self.modification_date,
            custom_fields=new_custom_fields
        )
