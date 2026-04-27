"""add bracket side fields

Revision ID: 0070706263c6
Revises: 1a9f9cf5faa1
Create Date: 2026-04-27 16:13:56.787570

"""
from collections.abc import Iterable
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '0070706263c6'
down_revision: Union[str, Sequence[str], None] = '1a9f9cf5faa1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    return table_name in inspector.get_table_names()


def _index_exists(
    inspector: sa.Inspector,
    table_name: str,
    index_name: str,
) -> bool:
    indexes = inspector.get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def _create_indexes() -> None:
    inspector = sa.inspect(op.get_bind())
    for index_name, table_name, columns in INDEX_TARGETS:
        if not _table_exists(inspector, table_name):
            continue
        if _index_exists(inspector, table_name, index_name):
            continue
        op.create_index(index_name, table_name, list(columns), unique=False)
        inspector = sa.inspect(op.get_bind())


def _drop_indexes() -> None:
    inspector = sa.inspect(op.get_bind())
    for index_name, table_name, _ in reversed(INDEX_TARGETS):
        if not _table_exists(inspector, table_name):
            continue
        if not _index_exists(inspector, table_name, index_name):
            continue
        op.drop_index(index_name, table_name=table_name)
        inspector = sa.inspect(op.get_bind())


def upgrade() -> None:
    """Upgrade schema."""
    _create_indexes()
    with op.batch_alter_table("matches", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tournament_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "bracket_side",
                sqlmodel.sql.sqltypes.AutoString(length=50),
                nullable=True,
            )
        )
        batch_op.create_index(
            batch_op.f("ix_matches_tournament_id"),
            ["tournament_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_matches_tournament_id_tournaments",
            "tournaments",
            ["tournament_id"],
            ["id"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("matches", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_matches_tournament_id_tournaments",
            type_="foreignkey",
        )
        batch_op.drop_index(batch_op.f("ix_matches_tournament_id"))
        batch_op.drop_column("bracket_side")
        batch_op.drop_column("tournament_id")
    _drop_indexes()
