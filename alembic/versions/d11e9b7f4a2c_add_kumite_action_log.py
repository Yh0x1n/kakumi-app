"""add_kumite_action_log

Revision ID: d11e9b7f4a2c
Revises: 9f9a87e71c72
Create Date: 2026-05-06 17:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d11e9b7f4a2c"
down_revision: Union[str, Sequence[str], None] = "9f9a87e71c72"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    """Return True when table exists in schema."""
    return table_name in inspector.get_table_names()


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    """Return True when table has named index."""
    indexes = inspector.get_indexes(table_name)
    return any(index.get("name") == index_name for index in indexes)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "match_action_logs"):
        op.create_table(
            "match_action_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("match_id", sa.Integer(), nullable=False),
            sa.Column("applied_by_id", sa.Integer(), nullable=True),
            sa.Column("action_kind", sa.String(length=50), nullable=False),
            sa.Column("participant", sa.String(length=10), nullable=True),
            sa.Column("before_snapshot", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["applied_by_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "match_action_logs") and not _has_index(
        inspector,
        "match_action_logs",
        op.f("ix_match_action_logs_match_id"),
    ):
        op.create_index(
            op.f("ix_match_action_logs_match_id"),
            "match_action_logs",
            ["match_id"],
            unique=False,
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "match_action_logs") and not _has_index(
        inspector,
        "match_action_logs",
        op.f("ix_match_action_logs_action_kind"),
    ):
        op.create_index(
            op.f("ix_match_action_logs_action_kind"),
            "match_action_logs",
            ["action_kind"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "match_action_logs") and _has_index(
        inspector,
        "match_action_logs",
        op.f("ix_match_action_logs_action_kind"),
    ):
        op.drop_index(
            op.f("ix_match_action_logs_action_kind"),
            table_name="match_action_logs",
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "match_action_logs") and _has_index(
        inspector,
        "match_action_logs",
        op.f("ix_match_action_logs_match_id"),
    ):
        op.drop_index(
            op.f("ix_match_action_logs_match_id"),
            table_name="match_action_logs",
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "match_action_logs"):
        op.drop_table("match_action_logs")
