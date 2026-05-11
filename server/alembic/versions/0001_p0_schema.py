"""Create P0 schema.

Revision ID: 0001_p0_schema
Revises:
Create Date: 2026-05-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_p0_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("avatar_asset_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="user"),
        sa.Column("storage_quota_bytes", sa.BigInteger(), nullable=True),
        sa.Column("used_storage_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("device_name", sa.String(length=128), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_table(
        "storage_locations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("base_path", sa.Text(), nullable=False),
        sa.Column("is_readonly", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "libraries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("storage_location_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("library_type", sa.String(length=32), nullable=False, server_default="managed"),
        sa.Column("root_path", sa.Text(), nullable=False),
        sa.Column("is_readonly", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("scan_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["storage_location_id"], ["storage_locations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("library_id", sa.Uuid(), nullable=True),
        sa.Column("asset_type", sa.String(length=16), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("file_hash", sa.String(length=128), nullable=False),
        sa.Column("device_asset_id", sa.Text(), nullable=True),
        sa.Column("device_id", sa.Uuid(), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("visibility", sa.String(length=32), nullable=False, server_default="private"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("ai_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("favorite", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_user_id", "file_hash", name="uq_assets_owner_hash"),
    )
    op.create_table(
        "asset_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("file_role", sa.String(length=32), nullable=False),
        sa.Column("storage_location_id", sa.Uuid(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["storage_location_id"], ["storage_locations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "file_role", name="uq_asset_files_asset_role"),
    )
    op.create_table(
        "upload_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=True),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("file_hash", sa.String(length=128), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("chunk_size", sa.Integer(), nullable=False),
        sa.Column("total_chunks", sa.Integer(), nullable=False),
        sa.Column("uploaded_chunks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="uploading"),
        sa.Column("target_library_id", sa.Uuid(), nullable=True),
        sa.Column("asset_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["target_library_id"], ["libraries.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "upload_parts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("upload_session_id", sa.Uuid(), nullable=False),
        sa.Column("part_index", sa.Integer(), nullable=False),
        sa.Column("part_size", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("temp_path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="uploaded"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["upload_session_id"], ["upload_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("upload_session_id", "part_index", name="uq_upload_parts_session_index"),
    )

    op.create_index("idx_refresh_tokens_user", "refresh_tokens", ["user_id"])
    op.create_index("idx_assets_owner_taken_at", "assets", ["owner_user_id", sa.text("taken_at DESC")])
    op.create_index("idx_assets_owner_hash", "assets", ["owner_user_id", "file_hash"])
    op.create_index("idx_assets_library", "assets", ["library_id"])
    op.create_index("idx_assets_ai_status", "assets", ["ai_status"])
    op.create_index("idx_asset_files_asset", "asset_files", ["asset_id"])
    op.create_index("idx_upload_sessions_user_status", "upload_sessions", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("idx_upload_sessions_user_status", table_name="upload_sessions")
    op.drop_index("idx_asset_files_asset", table_name="asset_files")
    op.drop_index("idx_assets_ai_status", table_name="assets")
    op.drop_index("idx_assets_library", table_name="assets")
    op.drop_index("idx_assets_owner_hash", table_name="assets")
    op.drop_index("idx_assets_owner_taken_at", table_name="assets")
    op.drop_index("idx_refresh_tokens_user", table_name="refresh_tokens")
    op.drop_table("upload_parts")
    op.drop_table("upload_sessions")
    op.drop_table("asset_files")
    op.drop_table("assets")
    op.drop_table("libraries")
    op.drop_table("storage_locations")
    op.drop_table("refresh_tokens")
    op.drop_table("users")

