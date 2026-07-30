"""add drawing texts table

Revision ID: e6b2c4d93a32
Revises: d5a1b3c92f21
Create Date: 2026-07-30 14:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6b2c4d93a32"
down_revision: Union[str, Sequence[str], None] = "d5a1b3c92f21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "drawing_texts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("drawing_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["drawing_id"], ["drawings.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("drawing_id", "page_number", name="uq_drawing_texts_drawing_page"),
    )


def downgrade() -> None:
    op.drop_table("drawing_texts")
