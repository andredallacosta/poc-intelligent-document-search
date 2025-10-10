"""add_user_authentication_fields

Revision ID: 39945b27c364
Revises: 1acc2f7e09b0
Create Date: 2025-10-08 14:30:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "39945b27c364"
down_revision = "e8a595f27b49"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new authentication fields to user table
    op.add_column(
        "user",
        sa.Column(
            "full_name", sa.String(length=255), nullable=False, server_default=""
        ),
    )
    op.add_column(
        "user",
        sa.Column("role", sa.String(length=20), nullable=False, server_default="user"),
    )
    op.add_column(
        "user", sa.Column("primary_municipality_id", sa.UUID(), nullable=True)
    )
    op.add_column(
        "user",
        sa.Column("municipality_ids", sa.JSON(), nullable=True, server_default="[]"),
    )
    op.add_column(
        "user",
        sa.Column(
            "auth_provider",
            sa.String(length=20),
            nullable=False,
            server_default="email_password",
        ),
    )
    op.add_column("user", sa.Column("google_id", sa.String(length=255), nullable=True))
    op.add_column(
        "user",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "user",
        sa.Column(
            "email_verified", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "user", sa.Column("last_login", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "user", sa.Column("invitation_token", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "user",
        sa.Column("invitation_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("user", sa.Column("invited_by", sa.UUID(), nullable=True))

    # Create foreign key constraints
    op.create_foreign_key(
        "fk_user_primary_municipality",
        "user",
        "municipality",
        ["primary_municipality_id"],
        ["id"],
    )
    op.create_foreign_key("fk_user_invited_by", "user", "user", ["invited_by"], ["id"])

    # Create new indexes
    op.create_index("idx_user_google_id", "user", ["google_id"])
    op.create_index("idx_user_invitation_token", "user", ["invitation_token"])
    op.create_index(
        "idx_user_primary_municipality", "user", ["primary_municipality_id"]
    )
    op.create_index("idx_user_role_active", "user", ["role", "is_active"])

    # Add check constraints
    op.create_check_constraint(
        "check_role_valid", "user", "role IN ('superuser', 'admin', 'user')"
    )
    op.create_check_constraint(
        "check_auth_provider_valid",
        "user",
        "auth_provider IN ('email_password', 'google_oauth2')",
    )
    op.create_check_constraint(
        "check_email_password_has_hash",
        "user",
        "(auth_provider = 'email_password' AND password_hash IS NOT NULL) OR (auth_provider = 'google_oauth2')",
    )
    op.create_check_constraint(
        "check_google_oauth_has_id",
        "user",
        "(auth_provider = 'google_oauth2' AND google_id IS NOT NULL) OR (auth_provider = 'email_password')",
    )
    op.create_check_constraint(
        "check_invitation_token_has_expiry",
        "user",
        "(invitation_token IS NULL AND invitation_expires_at IS NULL) OR (invitation_token IS NOT NULL AND invitation_expires_at IS NOT NULL)",
    )

    # Migrate existing data
    # Copy name to full_name
    op.execute('UPDATE "user" SET full_name = name WHERE name IS NOT NULL')

    # Copy municipality_id to primary_municipality_id and municipality_ids
    op.execute(
        'UPDATE "user" SET primary_municipality_id = municipality_id WHERE municipality_id IS NOT NULL'
    )
    op.execute(
        "UPDATE \"user\" SET municipality_ids = CASE WHEN municipality_id IS NOT NULL THEN json_build_array(municipality_id::text) ELSE '[]'::json END"
    )

    # Copy active to is_active
    op.execute('UPDATE "user" SET is_active = active WHERE active IS NOT NULL')

    # Update the idx_user_active index to use is_active instead of active
    op.drop_index("idx_user_active", table_name="user")
    op.create_index("idx_user_is_active", "user", ["is_active"])


def downgrade() -> None:
    # Remove check constraints
    op.drop_constraint("check_invitation_token_has_expiry", "user", type_="check")
    op.drop_constraint("check_google_oauth_has_id", "user", type_="check")
    op.drop_constraint("check_email_password_has_hash", "user", type_="check")
    op.drop_constraint("check_auth_provider_valid", "user", type_="check")
    op.drop_constraint("check_role_valid", "user", type_="check")

    # Remove indexes
    op.drop_index("idx_user_role_active", table_name="user")
    op.drop_index("idx_user_primary_municipality", table_name="user")
    op.drop_index("idx_user_invitation_token", table_name="user")
    op.drop_index("idx_user_google_id", table_name="user")
    op.drop_index("idx_user_is_active", table_name="user")

    # Remove foreign key constraints
    op.drop_constraint("fk_user_invited_by", "user", type_="foreignkey")
    op.drop_constraint("fk_user_primary_municipality", "user", type_="foreignkey")

    # Remove columns
    op.drop_column("user", "invited_by")
    op.drop_column("user", "invitation_expires_at")
    op.drop_column("user", "invitation_token")
    op.drop_column("user", "last_login")
    op.drop_column("user", "email_verified")
    op.drop_column("user", "is_active")
    op.drop_column("user", "google_id")
    op.drop_column("user", "auth_provider")
    op.drop_column("user", "municipality_ids")
    op.drop_column("user", "primary_municipality_id")
    op.drop_column("user", "role")
    op.drop_column("user", "full_name")

    # Recreate original idx_user_active index
    op.create_index("idx_user_active", "user", ["active"])
