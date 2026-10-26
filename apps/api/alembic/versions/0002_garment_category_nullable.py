"""garment category nullable

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-11

Deliberate, documented deviation from CLAUDE.md sec 4, which specifies `category VARCHAR
NOT NULL`. The upload-then-process flow (CLAUDE.md sec 8) creates the garment row in
`pending` status *before* vision analysis has run, so category is genuinely unknown at
creation time -- and if analysis later fails, the row must be able to stay without a
category (status=failed) rather than being blocked or getting an invented value. Making the
column nullable is required for that pipeline to work at all. The 6 allowed category values
(top/bottom/dress/outerwear/footwear/accessory) are still enforced at the application layer
by Pydantic validators (GarmentAnalysis, GarmentUpdate) whenever a category IS being set.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("garments", "category", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    op.alter_column("garments", "category", existing_type=sa.String(), nullable=False)
