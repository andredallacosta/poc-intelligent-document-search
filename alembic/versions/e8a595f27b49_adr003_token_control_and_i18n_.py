"""adr003_token_control_and_i18n_standardization

Revision ID: e8a595f27b49
Revises: 1acc2f7e09b0
Create Date: 2025-10-06 10:11:01.036750

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8a595f27b49"
down_revision: Union[str, Sequence[str], None] = "1acc2f7e09b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """ADR-003: Token Control + i18n Standardization"""

    # === STEP 1: RENAME TABLES TO ENGLISH ===

    # Rename prefeitura → municipality
    op.rename_table("prefeitura", "municipality")

    # Rename usuario → user
    op.rename_table("usuario", "user")

    # === STEP 2: RENAME COLUMNS TO ENGLISH ===

    # Municipality table columns
    op.alter_column("municipality", "nome", new_column_name="name")
    op.alter_column("municipality", "quota_tokens", new_column_name="token_quota")
    op.alter_column(
        "municipality", "tokens_consumidos", new_column_name="tokens_consumed"
    )
    op.alter_column("municipality", "ativo", new_column_name="active")
    op.alter_column("municipality", "criado_em", new_column_name="created_at")
    op.alter_column("municipality", "atualizado_em", new_column_name="updated_at")

    # User table columns
    op.alter_column("user", "prefeitura_id", new_column_name="municipality_id")
    op.alter_column("user", "nome", new_column_name="name")
    op.alter_column("user", "senha_hash", new_column_name="password_hash")
    op.alter_column("user", "ativo", new_column_name="active")
    op.alter_column("user", "criado_em", new_column_name="created_at")
    op.alter_column("user", "atualizado_em", new_column_name="updated_at")

    # Document table columns
    op.alter_column("documento", "titulo", new_column_name="title")
    op.alter_column("documento", "conteudo", new_column_name="content")
    op.alter_column("documento", "caminho_arquivo", new_column_name="file_path")
    op.alter_column("documento", "meta_data", new_column_name="metadata")
    op.alter_column("documento", "criado_em", new_column_name="created_at")
    op.alter_column("documento", "atualizado_em", new_column_name="updated_at")

    # Document chunk table columns
    op.alter_column("documento_chunk", "documento_id", new_column_name="document_id")
    op.alter_column("documento_chunk", "conteudo", new_column_name="content")
    op.alter_column("documento_chunk", "indice_chunk", new_column_name="chunk_index")
    op.alter_column("documento_chunk", "criado_em", new_column_name="created_at")

    # Document embedding table columns
    op.alter_column("documento_embedding", "criado_em", new_column_name="created_at")

    # Chat session table columns (already in English, just update references)
    op.alter_column("chat_session", "usuario_id", new_column_name="user_id")
    op.alter_column("chat_session", "ativo", new_column_name="active")
    op.alter_column("chat_session", "meta_data", new_column_name="metadata")
    op.alter_column("chat_session", "criado_em", new_column_name="created_at")
    op.alter_column("chat_session", "atualizado_em", new_column_name="updated_at")

    # Message table columns
    op.alter_column("message", "conteudo", new_column_name="content")
    op.alter_column("message", "tipo_mensagem", new_column_name="message_type")
    op.alter_column(
        "message", "referencias_documento", new_column_name="document_references"
    )
    op.alter_column("message", "tokens_usados", new_column_name="tokens_used")
    op.alter_column("message", "meta_data", new_column_name="metadata")
    op.alter_column("message", "criado_em", new_column_name="created_at")

    # === STEP 3: RENAME TABLES TO ENGLISH ===

    # Rename documento → document
    op.rename_table("documento", "document")

    # Rename documento_chunk → document_chunk
    op.rename_table("documento_chunk", "document_chunk")

    # Rename documento_embedding → document_embedding
    op.rename_table("documento_embedding", "document_embedding")

    # === STEP 4: ADD NEW FIELDS TO MUNICIPALITY FOR TOKEN CONTROL ===

    # Add new token control fields
    op.add_column(
        "municipality",
        sa.Column(
            "monthly_token_limit", sa.Integer(), nullable=False, server_default="20000"
        ),
    )
    op.add_column(
        "municipality",
        sa.Column(
            "contract_date",
            sa.Date(),
            nullable=False,
            server_default=sa.text("CURRENT_DATE"),
        ),
    )

    # Add constraints for new fields
    op.create_check_constraint(
        "check_monthly_limit_positive", "municipality", "monthly_token_limit > 0"
    )

    # === STEP 5: CREATE TOKEN_USAGE_PERIOD TABLE ===

    op.create_table(
        "token_usage_period",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("municipality_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("base_limit", sa.Integer(), nullable=False),
        sa.Column("extra_credits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_consumed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Foreign key
        sa.ForeignKeyConstraint(
            ["municipality_id"], ["municipality.id"], ondelete="CASCADE"
        ),
        # Business constraints
        sa.CheckConstraint("base_limit > 0", name="check_base_limit_positive"),
        sa.CheckConstraint(
            "extra_credits >= 0", name="check_extra_credits_non_negative"
        ),
        sa.CheckConstraint(
            "tokens_consumed >= 0", name="check_tokens_consumed_non_negative"
        ),
        sa.CheckConstraint("period_start < period_end", name="check_period_valid"),
        sa.CheckConstraint(
            "tokens_consumed <= (base_limit + extra_credits)",
            name="check_tokens_not_exceed_limit",
        ),
        # Unique constraint
        sa.UniqueConstraint(
            "municipality_id", "period_start", name="uq_municipality_period"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # === STEP 6: CREATE OPTIMIZED INDEXES ===

    # Indexes for token_usage_period
    op.create_index(
        "idx_token_period_current",
        "token_usage_period",
        ["municipality_id", "period_start", "period_end"],
    )
    op.create_index(
        "idx_token_period_active",
        "token_usage_period",
        ["municipality_id", "period_end"],
    )

    # Update existing indexes to use new names
    op.drop_index("idx_prefeitura_ativo", "municipality")
    op.create_index("idx_municipality_active", "municipality", ["active"])

    op.drop_index("idx_usuario_prefeitura", "user")
    op.create_index("idx_user_municipality", "user", ["municipality_id"])

    op.drop_index("idx_usuario_email", "user")
    op.create_index("idx_user_email", "user", ["email"])

    op.drop_index("idx_usuario_ativo", "user")
    op.create_index("idx_user_active", "user", ["active"])

    # Update document indexes
    op.drop_index("idx_documento_titulo", "document")
    op.create_index("idx_document_title", "document", ["title"])

    op.drop_index("idx_documento_file_hash", "document")
    op.create_index("idx_document_file_hash", "document", ["file_hash"])

    # Update session indexes
    op.drop_index("idx_session_usuario", "chat_session")
    op.create_index("idx_session_user", "chat_session", ["user_id"])

    op.drop_index("idx_session_created", "chat_session")
    op.create_index("idx_session_created", "chat_session", ["created_at"])


def downgrade() -> None:
    """Rollback ADR-003 changes"""

    # Drop new table
    op.drop_table("token_usage_period")

    # Remove new fields from municipality
    op.drop_column("municipality", "contract_date")
    op.drop_column("municipality", "monthly_token_limit")

    # Rename tables back to Portuguese
    op.rename_table("document_embedding", "documento_embedding")
    op.rename_table("document_chunk", "documento_chunk")
    op.rename_table("document", "documento")
    op.rename_table("user", "usuario")
    op.rename_table("municipality", "prefeitura")

    # Rename columns back to Portuguese (reverse order)
    # Message table
    op.alter_column("message", "created_at", new_column_name="criado_em")
    op.alter_column("message", "metadata", new_column_name="meta_data")
    op.alter_column("message", "tokens_used", new_column_name="tokens_usados")
    op.alter_column(
        "message", "document_references", new_column_name="referencias_documento"
    )
    op.alter_column("message", "message_type", new_column_name="tipo_mensagem")
    op.alter_column("message", "content", new_column_name="conteudo")

    # Chat session table
    op.alter_column("chat_session", "updated_at", new_column_name="atualizado_em")
    op.alter_column("chat_session", "created_at", new_column_name="criado_em")
    op.alter_column("chat_session", "metadata", new_column_name="meta_data")
    op.alter_column("chat_session", "active", new_column_name="ativo")
    op.alter_column("chat_session", "user_id", new_column_name="usuario_id")

    # Document embedding table
    op.alter_column("documento_embedding", "created_at", new_column_name="criado_em")

    # Document chunk table
    op.alter_column("documento_chunk", "created_at", new_column_name="criado_em")
    op.alter_column("documento_chunk", "chunk_index", new_column_name="indice_chunk")
    op.alter_column("documento_chunk", "content", new_column_name="conteudo")
    op.alter_column("documento_chunk", "document_id", new_column_name="documento_id")

    # Document table
    op.alter_column("documento", "updated_at", new_column_name="atualizado_em")
    op.alter_column("documento", "created_at", new_column_name="criado_em")
    op.alter_column("documento", "metadata", new_column_name="meta_data")
    op.alter_column("documento", "file_path", new_column_name="caminho_arquivo")
    op.alter_column("documento", "content", new_column_name="conteudo")
    op.alter_column("documento", "title", new_column_name="titulo")

    # User table
    op.alter_column("usuario", "updated_at", new_column_name="atualizado_em")
    op.alter_column("usuario", "created_at", new_column_name="criado_em")
    op.alter_column("usuario", "active", new_column_name="ativo")
    op.alter_column("usuario", "password_hash", new_column_name="senha_hash")
    op.alter_column("usuario", "name", new_column_name="nome")
    op.alter_column("usuario", "municipality_id", new_column_name="prefeitura_id")

    # Municipality table
    op.alter_column("prefeitura", "updated_at", new_column_name="atualizado_em")
    op.alter_column("prefeitura", "created_at", new_column_name="criado_em")
    op.alter_column("prefeitura", "active", new_column_name="ativo")
    op.alter_column(
        "prefeitura", "tokens_consumed", new_column_name="tokens_consumidos"
    )
    op.alter_column("prefeitura", "token_quota", new_column_name="quota_tokens")
    op.alter_column("prefeitura", "name", new_column_name="nome")
