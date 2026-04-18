"""add fk indexes

Revision ID: c078f55c0552
Revises: fe678c4071ac
Create Date: 2026-04-18 15:23:07.155787

"""

from collections.abc import Iterable
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c078f55c0552"
down_revision: Union[str, Sequence[str], None] = "fe678c4071ac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    _create_indexes()


def downgrade() -> None:
    """Downgrade schema."""
    _drop_indexes()


INDEX_TARGETS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("ix_athletes_kata_category_id", "athletes", ("kata_category_id",)),
    ("ix_athletes_kumite_category_id", "athletes", ("kumite_category_id",)),
    ("ix_matches_aka_id", "matches", ("aka_id",)),
    ("ix_matches_ao_id", "matches", ("ao_id",)),
    ("ix_matches_winner_id", "matches", ("winner_id",)),
    ("ix_matches_aka_team_id", "matches", ("aka_team_id",)),
    ("ix_matches_ao_team_id", "matches", ("ao_team_id",)),
    ("ix_matches_referee_id", "matches", ("referee_id",)),
    ("ix_matches_tatami_id", "matches", ("tatami_id",)),
    ("ix_match_scores_judge_id", "match_scores", ("judge_id",)),
    ("ix_match_scores_applied_by_id", "match_scores", ("applied_by_id",)),
    ("ix_penalties_given_by_id", "penalties", ("given_by_id",)),
    (
        "ix_tournament_categories_first_place_id",
        "tournament_categories",
        ("first_place_id",),
    ),
    (
        "ix_tournament_categories_second_place_id",
        "tournament_categories",
        ("second_place_id",),
    ),
    ("ix_token_blacklist_user_id", "token_blacklist", ("user_id",)),
    (
        "ix_tournament_event_logs_user_id",
        "tournament_event_logs",
        ("user_id",),
    ),
    ("ix_kata_judge_scores_performer_id", "kata_judge_scores", ("performer_id",)),
    ("ix_kata_judge_scores_team_id", "kata_judge_scores", ("team_id",)),
    (
        "ix_kata_round_standings_athlete_id",
        "kata_round_standings",
        ("athlete_id",),
    ),
    ("ix_kata_round_standings_team_id", "kata_round_standings", ("team_id",)),
)


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    """Return True when the target table exists."""
    return table_name in inspector.get_table_names()


def _index_exists(
    inspector: sa.Inspector,
    table_name: str,
    index_name: str,
) -> bool:
    """Return True when a named index already exists."""
    indexes = inspector.get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def _create_index(
    index_name: str,
    table_name: str,
    columns: Iterable[str],
) -> None:
    """Create index with dialect-safe behavior for PostgreSQL/SQLite."""
    context = op.get_context()
    if context.dialect.name == "postgresql":
        with context.autocommit_block():
            op.create_index(
                index_name,
                table_name,
                list(columns),
                unique=False,
                postgresql_concurrently=True,
            )
        return

    op.create_index(index_name, table_name, list(columns), unique=False)


def _drop_index(index_name: str, table_name: str) -> None:
    """Drop index with dialect-safe behavior for PostgreSQL/SQLite."""
    context = op.get_context()
    if context.dialect.name == "postgresql":
        with context.autocommit_block():
            op.drop_index(
                index_name,
                table_name=table_name,
                postgresql_concurrently=True,
            )
        return

    op.drop_index(index_name, table_name=table_name)


def _create_indexes() -> None:
    """Create all target FK indexes when table/index are available."""
    inspector = sa.inspect(op.get_bind())

    for index_name, table_name, columns in INDEX_TARGETS:
        if not _table_exists(inspector, table_name):
            continue
        if _index_exists(inspector, table_name, index_name):
            continue

        _create_index(index_name, table_name, columns)
        inspector = sa.inspect(op.get_bind())


def _drop_indexes() -> None:
    """Drop all target FK indexes when present."""
    inspector = sa.inspect(op.get_bind())

    for index_name, table_name, _ in reversed(INDEX_TARGETS):
        if not _table_exists(inspector, table_name):
            continue
        if not _index_exists(inspector, table_name, index_name):
            continue

        _drop_index(index_name, table_name)
        inspector = sa.inspect(op.get_bind())
