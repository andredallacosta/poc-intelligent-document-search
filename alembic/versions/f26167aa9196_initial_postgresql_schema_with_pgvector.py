"""Initial PostgreSQL schema with pgvector

Revision ID: f26167aa9196
Revises:
Create Date: 2025-09-16 22:35:52.127800

"""

from typing import Sequence, Union

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f26167aa9196"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create prefeitura table
    op.create_table(
        "prefeitura",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("quota_tokens", sa.Integer(), nullable=False, server_default="10000"),
        sa.Column("tokens_consumidos", sa.Integer(), server_default="0"),
        sa.Column("ativo", sa.Boolean(), server_default="true"),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "atualizado_em", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.CheckConstraint("quota_tokens >= 0", name="check_quota_positive"),
        sa.CheckConstraint("tokens_consumidos >= 0", name="check_tokens_positive"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_prefeitura_ativo", "prefeitura", ["ativo"])

    # Create usuario table
    op.create_table(
        "usuario",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("prefeitura_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default="true"),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "atualizado_em", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(
            ["prefeitura_id"],
            ["prefeitura.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("idx_usuario_ativo", "usuario", ["ativo"])
    op.create_index("idx_usuario_email", "usuario", ["email"])
    op.create_index("idx_usuario_prefeitura", "usuario", ["prefeitura_id"])

    # Create documento table
    op.create_table(
        "documento",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("titulo", sa.String(length=500), nullable=False),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("caminho_arquivo", sa.String(length=1000), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "meta_data", postgresql.JSON(astext_type=sa.Text()), server_default="{}"
        ),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "atualizado_em", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_hash", name="unique_file_hash"),
    )
    op.create_index("idx_documento_file_hash", "documento", ["file_hash"])
    op.create_index(
        "idx_documento_metadata_source",
        "documento",
        [sa.text("json_extract_path_text(meta_data, 'source')")],
    )
    op.create_index(
        "idx_documento_source_unique",
        "documento",
        [sa.text("json_extract_path_text(meta_data, 'source')")],
        unique=True,
    )
    op.create_index("idx_documento_titulo", "documento", ["titulo"])

    # Create documento_chunk table
    op.create_table(
        "documento_chunk",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("documento_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("indice_chunk", sa.Integer(), nullable=False),
        sa.Column("start_char", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("end_char", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "meta_data", postgresql.JSON(astext_type=sa.Text()), server_default="{}"
        ),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(["documento_id"], ["documento.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "documento_id", "indice_chunk", name="unique_chunk_per_document"
        ),
    )
    op.create_index("idx_chunk_documento", "documento_chunk", ["documento_id"])
    op.create_index(
        "idx_chunk_indice", "documento_chunk", ["documento_id", "indice_chunk"]
    )

    # Create documento_embedding table
    op.create_table(
        "documento_embedding",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["documento_chunk.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_embedding_chunk", "documento_embedding", ["chunk_id"], unique=True
    )

    # Create chat_session table
    op.create_table(
        "chat_session",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default="true"),
        sa.Column(
            "meta_data", postgresql.JSON(astext_type=sa.Text()), server_default="{}"
        ),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "atualizado_em", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_session_ativo", "chat_session", ["ativo"])
    op.create_index("idx_session_created", "chat_session", ["criado_em"])
    op.create_index("idx_session_usuario", "chat_session", ["usuario_id"])

    # Create message table
    op.create_table(
        "message",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("tipo_mensagem", sa.String(length=50), server_default="text"),
        sa.Column(
            "referencias_documento",
            postgresql.JSON(astext_type=sa.Text()),
            server_default="[]",
        ),
        sa.Column("tokens_usados", sa.Integer(), server_default="0"),
        sa.Column(
            "meta_data", postgresql.JSON(astext_type=sa.Text()), server_default="{}"
        ),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant', 'system')", name="check_valid_role"
        ),
        sa.CheckConstraint("tokens_usados >= 0", name="check_tokens_positive"),
        sa.ForeignKeyConstraint(
            ["session_id"], ["chat_session.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_message_created", "message", ["criado_em"])
    op.create_index("idx_message_role", "message", ["role"])
    op.create_index("idx_message_session", "message", ["session_id"])

    # Create vector index for similarity search (IVFFlat)
    # Note: This should be created after data is inserted for better performance
    op.execute(
        "CREATE INDEX idx_documento_embedding_vector ON documento_embedding USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("message")
    op.drop_table("chat_session")
    op.drop_table("documento_embedding")
    op.drop_table("documento_chunk")
    op.drop_table("documento")
    op.drop_table("usuario")
    op.drop_table("prefeitura")

    # Drop extension
    op.execute("DROP EXTENSION IF EXISTS vector")
