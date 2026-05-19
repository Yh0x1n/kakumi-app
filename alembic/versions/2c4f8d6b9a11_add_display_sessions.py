"""add display sessions table

Revision ID: 2c4f8d6b9a11
Revises: 5f6a7b8c9d10
Create Date: 2026-05-19 18:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2c4f8d6b9a11"
down_revision: Union[str, Sequence[str], None] = "5f6a7b8c9d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    indexes = inspector.get_indexes(table_name)
    return any(index.get("name") == index_name for index in indexes)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "display_sessions"):
        op.create_table(
            "display_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("display_key", sa.String(length=64), nullable=False),
            sa.Column("modality", sa.String(length=16), nullable=False),
            sa.Column("source_kind", sa.String(length=16), nullable=False),
            sa.Column("match_id", sa.Integer(), nullable=True),
            sa.Column("snapshot_json", sa.String(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("display_key"),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "display_sessions") and not _has_index(
        inspector,
        "display_sessions",
        op.f("ix_display_sessions_display_key"),
    ):
        op.create_index(
            op.f("ix_display_sessions_display_key"),
            "display_sessions",
            ["display_key"],
            unique=True,
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "display_sessions") and not _has_index(
        inspector,
        "display_sessions",
        op.f("ix_display_sessions_modality"),
    ):
        op.create_index(
            op.f("ix_display_sessions_modality"),
            "display_sessions",
            ["modality"],
            unique=False,
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "display_sessions") and not _has_index(
        inspector,
        "display_sessions",
        op.f("ix_display_sessions_source_kind"),
    ):
        op.create_index(
            op.f("ix_display_sessions_source_kind"),
            "display_sessions",
            ["source_kind"],
            unique=False,
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "display_sessions") and not _has_index(
        inspector,
        "display_sessions",
        op.f("ix_display_sessions_match_id"),
    ):
        op.create_index(
            op.f("ix_display_sessions_match_id"),
            "display_sessions",
            ["match_id"],
            unique=False,
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "display_sessions") and not _has_index(
        inspector,
        "display_sessions",
        op.f("ix_display_sessions_updated_at"),
    ):
        op.create_index(
            op.f("ix_display_sessions_updated_at"),
            "display_sessions",
            ["updated_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "display_sessions") and _has_index(
        inspector,
        "display_sessions",
        op.f("ix_display_sessions_updated_at"),
    ):
        op.drop_index(op.f("ix_display_sessions_updated_at"), table_name="display_sessions")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "display_sessions") and _has_index(
        inspector,
        "display_sessions",
        op.f("ix_display_sessions_match_id"),
    ):
        op.drop_index(op.f("ix_display_sessions_match_id"), table_name="display_sessions")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "display_sessions") and _has_index(
        inspector,
        "display_sessions",
        op.f("ix_display_sessions_source_kind"),
    ):
        op.drop_index(
            op.f("ix_display_sessions_source_kind"),
            table_name="display_sessions",
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "display_sessions") and _has_index(
        inspector,
        "display_sessions",
        op.f("ix_display_sessions_modality"),
    ):
        op.drop_index(op.f("ix_display_sessions_modality"), table_name="display_sessions")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "display_sessions") and _has_index(
        inspector,
        "display_sessions",
        op.f("ix_display_sessions_display_key"),
    ):
        op.drop_index(
            op.f("ix_display_sessions_display_key"),
            table_name="display_sessions",
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "display_sessions"):
        op.drop_table("display_sessions")
