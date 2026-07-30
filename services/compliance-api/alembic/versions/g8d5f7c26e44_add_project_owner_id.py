"""add project owner_id

Revision ID: g8d5f7c26e44
Revises: f7c4e6b15d33
Create Date: 2026-07-30 15:15:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g8d5f7c26e44"
down_revision: Union[str, Sequence[str], None] = "f7c4e6b15d33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_projects_owner_id_users",
        "projects",
        "users",
        ["owner_id"],
        ["id"],
    )

    bind = op.get_bind()
    projects = sa.table(
        "projects",
        sa.column("id", sa.Integer()),
        sa.column("owner_id", sa.Integer()),
    )
    users = sa.table(
        "users",
        sa.column("id", sa.Integer()),
        sa.column("email", sa.String()),
        sa.column("hashed_password", sa.String()),
        sa.column("created_at", sa.DateTime()),
    )

    orphan_project_ids = bind.execute(
        sa.select(projects.c.id).where(projects.c.owner_id.is_(None))
    ).scalars().all()

    if orphan_project_ids:
        legacy_owner_id = bind.execute(sa.select(users.c.id).limit(1)).scalar_one_or_none()
        if legacy_owner_id is None:
            from datetime import UTC, datetime

            legacy_owner_id = bind.execute(
                sa.insert(users)
                .values(
                    email="legacy-owner@example.com",
                    hashed_password="!",
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                )
                .returning(users.c.id)
            ).scalar_one()

        bind.execute(
            sa.update(projects)
            .where(projects.c.owner_id.is_(None))
            .values(owner_id=legacy_owner_id)
        )

    op.alter_column("projects", "owner_id", nullable=False)


def downgrade() -> None:
    op.drop_constraint("fk_projects_owner_id_users", "projects", type_="foreignkey")
    op.drop_column("projects", "owner_id")
