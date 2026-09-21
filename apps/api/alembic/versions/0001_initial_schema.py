"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-18

Creates every MVP table from CLAUDE.md section 4, enables pgcrypto + vector, and adds an HNSW
cosine index on garment_embeddings. The embedding column width comes from the EMBEDDING_DIMENSION
env var (falling back to 1536) so it always matches whatever embedding model is configured —
it is read at migration-run time, not hard-coded.
"""
import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", "1536"))


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    uuid_pk = lambda: sa.Column(  # noqa: E731
        "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )

    op.create_table(
        "users",
        uuid_pk(),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "user_profiles",
        uuid_pk(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("height_cm", sa.Numeric, nullable=True),
        sa.Column("body_shape", sa.String, nullable=True),
        sa.Column("preferred_fit", sa.String, nullable=False, server_default="regular"),
        sa.Column("preferred_styles", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("preferred_colors", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("disliked_colors", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("style_preferences", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "avatars",
        uuid_pk(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_url", sa.Text, nullable=False),
        sa.Column("type", sa.String, nullable=False, server_default="full_body"),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("metadata", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_avatars_user_id", "avatars", ["user_id"])

    op.create_table(
        "garments",
        uuid_pk(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String, nullable=True),
        sa.Column("category", sa.String, nullable=False),
        sa.Column("subcategory", sa.String, nullable=True),
        sa.Column("colors", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("pattern", sa.String, nullable=True),
        sa.Column("material", sa.String, nullable=True),
        sa.Column("fit", sa.String, nullable=True),
        sa.Column("formality", sa.Numeric(3, 2), nullable=True),
        sa.Column("seasons", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("style_tags", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("processing_status", sa.String, nullable=False, server_default="pending"),
        sa.Column("processing_error", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_garments_user_id", "garments", ["user_id"])
    op.create_index("ix_garments_category", "garments", ["category"])
    op.create_index("ix_garments_processing_status", "garments", ["processing_status"])

    op.create_table(
        "garment_images",
        uuid_pk(),
        sa.Column("garment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("garments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_url", sa.Text, nullable=False),
        sa.Column("image_type", sa.String, nullable=False, server_default="original"),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("width", sa.Integer, nullable=True),
        sa.Column("height", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_garment_images_garment_id", "garment_images", ["garment_id"])

    op.create_table(
        "garment_embeddings",
        uuid_pk(),
        sa.Column("garment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("garments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=False),
        sa.Column("embedding_model", sa.String, nullable=False),
        sa.Column("embedding_text", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute(
        "CREATE INDEX ix_garment_embeddings_embedding_hnsw ON garment_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "style_requests",
        uuid_pk(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("occasion", sa.String, nullable=True),
        sa.Column("formality", sa.Numeric(3, 2), nullable=True),
        sa.Column("vibes", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("constraints", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("parsed_intent", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_style_requests_user_id", "style_requests", ["user_id"])

    op.create_table(
        "outfits",
        uuid_pk(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("style_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("style_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("occasion", sa.String, nullable=True),
        sa.Column("vibe", sa.String, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("score", sa.Numeric(5, 4), nullable=True),
        sa.Column("scoring_breakdown", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("status", sa.String, nullable=False, server_default="generated"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_outfits_user_id", "outfits", ["user_id"])

    op.create_table(
        "outfit_items",
        uuid_pk(),
        sa.Column("outfit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outfits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("garment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("garments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String, nullable=True),
        sa.Column("position", sa.Integer, nullable=True),
        sa.UniqueConstraint("outfit_id", "garment_id", name="uq_outfit_garment"),
    )
    op.create_index("ix_outfit_items_outfit_id", "outfit_items", ["outfit_id"])
    op.create_index("ix_outfit_items_garment_id", "outfit_items", ["garment_id"])

    op.create_table(
        "outfit_feedback",
        uuid_pk(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("outfit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outfits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feedback", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "outfit_id", "feedback", name="uq_user_outfit_feedback"),
    )
    op.create_index("ix_outfit_feedback_user_id", "outfit_feedback", ["user_id"])
    op.create_index("ix_outfit_feedback_outfit_id", "outfit_feedback", ["outfit_id"])

    op.create_table(
        "try_on_jobs",
        uuid_pk(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("outfit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outfits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("avatar_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("avatars.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String, nullable=False, server_default="pending"),
        sa.Column("result_image_url", sa.Text, nullable=True),
        sa.Column("provider", sa.String, nullable=True),
        sa.Column("provider_job_id", sa.String, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_try_on_jobs_user_id", "try_on_jobs", ["user_id"])
    op.create_index("ix_try_on_jobs_status", "try_on_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("try_on_jobs")
    op.drop_table("outfit_feedback")
    op.drop_table("outfit_items")
    op.drop_table("outfits")
    op.drop_table("style_requests")
    op.drop_table("garment_embeddings")
    op.drop_table("garment_images")
    op.drop_table("garments")
    op.drop_table("avatars")
    op.drop_table("user_profiles")
    op.drop_table("users")
