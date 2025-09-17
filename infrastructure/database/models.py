from datetime import datetime
from typing import Dict, Any
from uuid import uuid4
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, ForeignKey, 
    Index, UniqueConstraint, CheckConstraint, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class PrefeituraModel(Base):
    __tablename__ = "prefeitura"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    nome = Column(String(255), nullable=False)
    quota_tokens = Column(Integer, nullable=False, default=10000)
    tokens_consumidos = Column(Integer, default=0)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_prefeitura_ativo', 'ativo'),
        CheckConstraint('quota_tokens >= 0', name='check_quota_positive'),
        CheckConstraint('tokens_consumidos >= 0', name='check_tokens_positive'),
    )


class UsuarioModel(Base):
    __tablename__ = "usuario"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    prefeitura_id = Column(UUID(as_uuid=True), ForeignKey('prefeitura.id'), nullable=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=True)  # NULL até implementar auth
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_usuario_prefeitura', 'prefeitura_id'),
        Index('idx_usuario_email', 'email'),
        Index('idx_usuario_ativo', 'ativo'),
    )


class DocumentoModel(Base):
    __tablename__ = "documento"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    titulo = Column(String(500), nullable=False)
    conteudo = Column(Text, nullable=False)
    caminho_arquivo = Column(String(1000), nullable=False)
    file_hash = Column(String(64), nullable=True)  # SHA256 para controle duplicação
    meta_data = Column(JSON, default=dict)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_documento_titulo', 'titulo'),
        Index('idx_documento_file_hash', 'file_hash'),
        Index('idx_documento_metadata_source', func.json_extract_path_text('meta_data', 'source')),
        UniqueConstraint('file_hash', name='unique_file_hash'),
        # Constraint para source único (quando não NULL)
        Index('idx_documento_source_unique', func.json_extract_path_text('meta_data', 'source'), unique=True),
    )


class DocumentoChunkModel(Base):
    __tablename__ = "documento_chunk"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    documento_id = Column(UUID(as_uuid=True), ForeignKey('documento.id', ondelete='CASCADE'), nullable=False)
    conteudo = Column(Text, nullable=False)
    indice_chunk = Column(Integer, nullable=False)
    start_char = Column(Integer, nullable=False, default=0)
    end_char = Column(Integer, nullable=False, default=0)
    meta_data = Column(JSON, default=dict)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_chunk_documento', 'documento_id'),
        Index('idx_chunk_indice', 'documento_id', 'indice_chunk'),
        UniqueConstraint('documento_id', 'indice_chunk', name='unique_chunk_per_document'),
    )


class DocumentoEmbeddingModel(Base):
    __tablename__ = "documento_embedding"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey('documento_chunk.id', ondelete='CASCADE'), nullable=False)
    embedding = Column(Vector(1536), nullable=False)  # OpenAI text-embedding-3-small
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_embedding_chunk', 'chunk_id', unique=True),
        # Índice IVFFlat para busca vetorial (será criado via migration)
        # CREATE INDEX idx_documento_embedding_vector ON documento_embedding USING ivfflat (embedding vector_cosine_ops);
    )


class ChatSessionModel(Base):
    __tablename__ = "chat_session"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey('usuario.id'), nullable=True)  # NULL para sessões anônimas
    ativo = Column(Boolean, default=True)
    meta_data = Column(JSON, default=dict)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_session_usuario', 'usuario_id'),
        Index('idx_session_ativo', 'ativo'),
        Index('idx_session_created', 'criado_em'),
    )


class MessageModel(Base):
    __tablename__ = "message"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('chat_session.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(20), nullable=False)
    conteudo = Column(Text, nullable=False)
    tipo_mensagem = Column(String(50), default='text')
    referencias_documento = Column(JSON, default=list)
    tokens_usados = Column(Integer, default=0)
    meta_data = Column(JSON, default=dict)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_message_session', 'session_id'),
        Index('idx_message_created', 'criado_em'),
        Index('idx_message_role', 'role'),
        CheckConstraint("role IN ('user', 'assistant', 'system')", name='check_valid_role'),
        CheckConstraint('tokens_usados >= 0', name='check_tokens_positive'),
    )
