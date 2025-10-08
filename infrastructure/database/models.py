from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class MunicipalityModel(Base):
    __tablename__ = "municipality"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    token_quota = Column(Integer, nullable=False, default=10000)
    tokens_consumed = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    monthly_token_limit = Column(Integer, default=20000)
    contract_date = Column(Date, server_default=func.current_date())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_municipality_active", "active"),
        CheckConstraint("token_quota >= 0", name="check_quota_positive"),
        CheckConstraint("tokens_consumed >= 0", name="check_tokens_positive"),
        CheckConstraint("monthly_token_limit > 0", name="check_monthly_limit_positive"),
    )


class UserModel(Base):
    __tablename__ = "user"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    municipality_id = Column(
        UUID(as_uuid=True), ForeignKey("municipality.id"), nullable=True
    )
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_user_municipality", "municipality_id"),
        Index("idx_user_email", "email"),
        Index("idx_user_active", "active"),
    )


class DocumentModel(Base):
    __tablename__ = "document"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_hash = Column(String(64), nullable=True)
    meta_data = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_document_title", "title"),
        Index("idx_document_file_hash", "file_hash"),
        Index(
            "idx_document_metadata_source",
            func.json_extract_path_text("meta_data", "source"),
        ),
        UniqueConstraint("file_hash", name="unique_file_hash"),
        Index(
            "idx_document_source_unique",
            func.json_extract_path_text("meta_data", "source"),
            unique=True,
        ),
    )


class DocumentChunkModel(Base):
    __tablename__ = "document_chunk"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document.id", ondelete="CASCADE"),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    start_char = Column(Integer, nullable=False, default=0)
    end_char = Column(Integer, nullable=False, default=0)
    meta_data = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_chunk_document", "document_id"),
        Index("idx_chunk_index", "document_id", "chunk_index"),
        UniqueConstraint(
            "document_id", "chunk_index", name="unique_chunk_per_document"
        ),
    )


class DocumentEmbeddingModel(Base):
    __tablename__ = "document_embedding"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    chunk_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_chunk.id", ondelete="CASCADE"),
        nullable=False,
    )
    embedding = Column(Vector(1536), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_embedding_chunk", "chunk_id", unique=True),)


class ChatSessionModel(Base):
    __tablename__ = "chat_session"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    active = Column(Boolean, default=True)
    meta_data = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_session_user", "user_id"),
        Index("idx_session_active", "active"),
        Index("idx_session_created", "created_at"),
    )


class MessageModel(Base):
    __tablename__ = "message"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat_session.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(50), default="text")
    document_references = Column(JSON, default=list)
    tokens_used = Column(Integer, default=0)
    meta_data = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_message_session", "session_id"),
        Index("idx_message_created", "created_at"),
        Index("idx_message_role", "role"),
        CheckConstraint(
            "role IN ('user', 'assistant', 'system')", name="check_valid_role"
        ),
        CheckConstraint("tokens_used >= 0", name="check_tokens_positive"),
    )


class FileUploadModel(Base):
    __tablename__ = "file_upload"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(UUID(as_uuid=True), nullable=False)
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String(100), nullable=False)
    s3_bucket = Column(String(63), nullable=True)
    s3_key = Column(String(1024), nullable=True)
    s3_region = Column(String(50), nullable=True)
    upload_url = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_file_upload_document_id", "document_id"),
        Index("idx_file_upload_created", "created_at"),
        CheckConstraint("file_size > 0", name="check_file_size_positive"),
    )


class DocumentProcessingJobModel(Base):
    __tablename__ = "document_processing_job"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(UUID(as_uuid=True), nullable=False)
    upload_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(50), nullable=False, default="uploaded")
    current_step = Column(String(500), nullable=False, default="")
    progress = Column(Integer, nullable=False, default=0)
    chunks_processed = Column(Integer, nullable=False, default=0)
    total_chunks = Column(Integer, nullable=False, default=0)
    processing_time_seconds = Column(Integer, nullable=False, default=0)
    s3_file_deleted = Column(Boolean, default=False)
    duplicate_of = Column(UUID(as_uuid=True), nullable=True)
    content_hash_algorithm = Column(String(20), nullable=True)
    content_hash_value = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    meta_data = Column("meta_data", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_processing_job_document_id", "document_id"),
        Index("idx_processing_job_upload_id", "upload_id"),
        Index("idx_processing_job_status", "status"),
        Index("idx_processing_job_created", "created_at"),
        CheckConstraint(
            "progress >= 0 AND progress <= 100", name="check_progress_range"
        ),
        CheckConstraint(
            "chunks_processed >= 0", name="check_chunks_processed_positive"
        ),
        CheckConstraint("total_chunks >= 0", name="check_total_chunks_positive"),
        CheckConstraint(
            "processing_time_seconds >= 0", name="check_processing_time_positive"
        ),
        CheckConstraint(
            "status IN ('uploaded', 'extracting', 'checking_duplicates', 'chunking', 'embedding', 'completed', 'failed', 'duplicate')",
            name="check_valid_status",
        ),
    )


class TokenUsagePeriodModel(Base):
    __tablename__ = "token_usage_period"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    municipality_id = Column(
        UUID(as_uuid=True),
        ForeignKey("municipality.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    base_limit = Column(Integer, nullable=False)
    extra_credits = Column(Integer, default=0)
    tokens_consumed = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index(
            "idx_token_period_current", "municipality_id", "period_start", "period_end"
        ),
        Index("idx_token_period_active", "municipality_id", "period_end"),
        CheckConstraint("base_limit > 0", name="check_base_limit_positive"),
        CheckConstraint("extra_credits >= 0", name="check_extra_credits_non_negative"),
        CheckConstraint(
            "tokens_consumed >= 0", name="check_tokens_consumed_non_negative"
        ),
        CheckConstraint("period_start < period_end", name="check_period_valid"),
        CheckConstraint(
            "tokens_consumed <= (base_limit + extra_credits)",
            name="check_tokens_not_exceed_limit",
        ),
        UniqueConstraint(
            "municipality_id", "period_start", name="uq_municipality_period"
        ),
    )
