"""add room travel distance sprinklered and exits table

Revision ID: b8e4c1a27f3d
Revises: 3659450edc05
Create Date: 2026-07-30 14:21:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8e4c1a27f3d"
down_revision: Union[str, Sequence[str], None] = "3659450edc05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "rooms",
        sa.Column("travel_distance", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "rooms",
        sa.Column("sprinklered", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "exits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("clear_width", sa.Float(), nullable=False),
        sa.Column("is_required_exit", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.alter_column("rooms", "travel_distance", server_default=None)
    op.alter_column("rooms", "sprinklered", server_default=None)
    op.alter_column("exits", "is_required_exit", server_default=None)


def downgrade() -> None:
    op.drop_table("exits")
    op.drop_column("rooms", "sprinklered")
    op.drop_column("rooms", "travel_distance")
