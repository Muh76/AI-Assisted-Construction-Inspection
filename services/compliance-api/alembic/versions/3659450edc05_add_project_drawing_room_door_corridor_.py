"""add project drawing room door corridor tables

Revision ID: 3659450edc05
Revises: 397a5baa433c
Create Date: 2026-07-30 11:22:14.685213

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3659450edc05"
down_revision: Union[str, Sequence[str], None] = "397a5baa433c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

drawing_type_enum = sa.Enum(
    "architectural",
    "mechanical",
    name="drawing_type",
)


def upgrade() -> None:
    drawing_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "corridors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("clear_width", sa.Float(), nullable=False),
        sa.Column("length", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "drawings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("type", drawing_type_enum, nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("upload_date", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("occupancy_category", sa.String(length=64), nullable=False),
        sa.Column("floor_area", sa.Float(), nullable=False),
        sa.Column("occupant_load", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "doors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("clear_width", sa.Float(), nullable=False),
        sa.Column("fire_rating", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("doors")
    op.drop_table("rooms")
    op.drop_table("drawings")
    op.drop_table("corridors")
    op.drop_table("projects")
    drawing_type_enum.drop(op.get_bind(), checkfirst=True)
