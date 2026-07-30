"""add fire protection items table

Revision ID: c4f9a2d81e10
Revises: b8e4c1a27f3d
Create Date: 2026-07-30 14:22:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4f9a2d81e10"
down_revision: Union[str, Sequence[str], None] = "b8e4c1a27f3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

fire_protection_item_type_enum = postgresql.ENUM(
    "fire_extinguisher",
    "penetration_seal",
    "fire_separation",
    name="fire_protection_item_type",
    create_type=False,
)


def upgrade() -> None:
    fire_protection_item_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "fire_protection_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("item_type", fire_protection_item_type_enum, nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("rating_required", sa.String(length=64), nullable=True),
        sa.Column("rating_provided", sa.String(length=64), nullable=True),
        sa.Column("travel_distance_to_nearest", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("fire_protection_items")
    fire_protection_item_type_enum.drop(op.get_bind(), checkfirst=True)
