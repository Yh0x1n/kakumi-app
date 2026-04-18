"""add_penalty_system_fields

Revision ID: b1f4a2d9c8e1
Revises: effb5c40a98c
Create Date: 2026-04-18 13:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b1f4a2d9c8e1"
down_revision: Union[str, Sequence[str], None] = "effb5c40a98c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    """Return True when table exists in current schema."""
    return table_name in inspector.get_table_names()


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    """Return True when table contains the given column."""
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    return column_name in columns


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    """Return True when table already has an index with index_name."""
    indexes = inspector.get_indexes(table_name)
    return any(index.get("name") == index_name for index in indexes)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "athletes") and not _has_column(
        inspector,
        "athletes",
        "is_disqualified",
    ):
        op.add_column(
            "athletes",
            sa.Column(
                "is_disqualified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "tournaments") and not _has_column(
        inspector,
        "tournaments",
        "scheduling_gap_seconds",
    ):
        op.add_column(
            "tournaments",
            sa.Column(
                "scheduling_gap_seconds",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("75"),
            ),
        )

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "standings_delta_logs"):
        op.create_table(
            "standings_delta_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("athlete_id", sa.Integer(), nullable=False),
            sa.Column("change_key", sa.String(), nullable=False),
            sa.Column("before_snapshot", sa.String(), nullable=False),
            sa.Column("applied_at", sa.DateTime(), nullable=False),
            sa.Column("tournament_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
            sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_standings_delta_logs_athlete_id"),
            "standings_delta_logs",
            ["athlete_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_standings_delta_logs_change_key"),
            "standings_delta_logs",
            ["change_key"],
            unique=False,
        )
        op.create_index(
            op.f("ix_standings_delta_logs_tournament_id"),
            "standings_delta_logs",
            ["tournament_id"],
            unique=False,
        )

    inspector = sa.inspect(bind)
    if (
        _has_table(inspector, "penalties")
        and _has_column(inspector, "penalties", "match_id")
        and _has_column(inspector, "penalties", "participant")
        and not _has_index(
            inspector,
            "penalties",
            "ix_penalties_match_participant",
        )
    ):
        op.create_index(
            "ix_penalties_match_participant",
            "penalties",
            ["match_id", "participant"],
            unique=False,
        )

    inspector = sa.inspect(bind)
    if (
        _has_table(inspector, "matches")
        and _has_column(inspector, "matches", "tatami_id")
        and _has_column(inspector, "matches", "start_time")
        and not _has_index(
            inspector,
            "matches",
            "ix_matches_tatami_start_time",
        )
    ):
        op.create_index(
            "ix_matches_tatami_start_time",
            "matches",
            ["tatami_id", "start_time"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "matches") and _has_index(
        inspector,
        "matches",
        "ix_matches_tatami_start_time",
    ):
        op.drop_index("ix_matches_tatami_start_time", table_name="matches")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "penalties") and _has_index(
        inspector,
        "penalties",
        "ix_penalties_match_participant",
    ):
        op.drop_index("ix_penalties_match_participant", table_name="penalties")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "standings_delta_logs"):
        if _has_index(
            inspector,
            "standings_delta_logs",
            op.f("ix_standings_delta_logs_tournament_id"),
        ):
            op.drop_index(
                op.f("ix_standings_delta_logs_tournament_id"),
                table_name="standings_delta_logs",
            )
        if _has_index(
            inspector,
            "standings_delta_logs",
            op.f("ix_standings_delta_logs_change_key"),
        ):
            op.drop_index(
                op.f("ix_standings_delta_logs_change_key"),
                table_name="standings_delta_logs",
            )
        if _has_index(
            inspector,
            "standings_delta_logs",
            op.f("ix_standings_delta_logs_athlete_id"),
        ):
            op.drop_index(
                op.f("ix_standings_delta_logs_athlete_id"),
                table_name="standings_delta_logs",
            )
        op.drop_table("standings_delta_logs")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "tournaments") and _has_column(
        inspector,
        "tournaments",
        "scheduling_gap_seconds",
    ):
        op.drop_column("tournaments", "scheduling_gap_seconds")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "athletes") and _has_column(
        inspector,
        "athletes",
        "is_disqualified",
    ):
        op.drop_column("athletes", "is_disqualified")
