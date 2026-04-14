"""add_kata_scoring

Revision ID: a8c4641d867d
Revises: f0988d9c3f59
Create Date: 2026-04-13 22:07:36.539376

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a8c4641d867d"
down_revision: Union[str, Sequence[str], None] = "f0988d9c3f59"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    """Retorna True si tabla existe."""
    return table_name in inspector.get_table_names()


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    """Retorna True si columna existe en tabla."""
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    return column_name in columns


def _has_fk(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    """Retorna True si FK con nombre existe en tabla."""
    fks = inspector.get_foreign_keys(table_name)
    return any((fk.get("name") or "") == constraint_name for fk in fks)


def _create_kata_tables(inspector: sa.Inspector) -> None:
    """Crea tablas de kata si no existen."""
    if not _has_table(inspector, "kata_judge_scores"):
        op.create_table(
            "kata_judge_scores",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("judge_id", sa.Integer(), nullable=False),
            sa.Column("match_id", sa.Integer(), nullable=False),
            sa.Column("performer_id", sa.Integer(), nullable=True),
            sa.Column("team_id", sa.Integer(), nullable=True),
            sa.Column("participant", sa.String(), nullable=False),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("flag_vote", sa.String(), nullable=True),
            sa.Column("is_flag_mode", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["judge_id"], ["referees.id"]),
            sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
            sa.ForeignKeyConstraint(["performer_id"], ["athletes.id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_kata_judge_scores_judge_id"),
            "kata_judge_scores",
            ["judge_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_kata_judge_scores_match_id"),
            "kata_judge_scores",
            ["match_id"],
            unique=False,
        )

    if not _has_table(inspector, "kata_round_standings"):
        op.create_table(
            "kata_round_standings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("match_id", sa.Integer(), nullable=False),
            sa.Column("athlete_id", sa.Integer(), nullable=True),
            sa.Column("team_id", sa.Integer(), nullable=True),
            sa.Column("victory_points", sa.Integer(), nullable=False),
            sa.Column("votes_received", sa.Integer(), nullable=False),
            sa.Column("needs_extra_kata", sa.Boolean(), nullable=False),
            sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
            sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_kata_round_standings_match_id"),
            "kata_round_standings",
            ["match_id"],
            unique=False,
        )


def _alter_matches(inspector: sa.Inspector) -> None:
    """Agrega columnas/FK de Team Kata sobre matches."""
    if not _has_column(inspector, "matches", "aka_team_id"):
        op.add_column("matches", sa.Column("aka_team_id", sa.Integer(), nullable=True))
    if not _has_column(inspector, "matches", "ao_team_id"):
        op.add_column("matches", sa.Column("ao_team_id", sa.Integer(), nullable=True))
    if not _has_column(inspector, "matches", "bunkai_required"):
        op.add_column(
            "matches",
            sa.Column(
                "bunkai_required",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )

    inspector = sa.inspect(op.get_bind())
    needs_aka_fk = not _has_fk(inspector, "matches", "fk_matches_aka_team_id_teams")
    needs_ao_fk = not _has_fk(inspector, "matches", "fk_matches_ao_team_id_teams")
    if needs_aka_fk or needs_ao_fk:
        with op.batch_alter_table("matches", recreate="always") as batch_op:
            if needs_aka_fk:
                batch_op.create_foreign_key(
                    "fk_matches_aka_team_id_teams",
                    "teams",
                    ["aka_team_id"],
                    ["id"],
                )
            if needs_ao_fk:
                batch_op.create_foreign_key(
                    "fk_matches_ao_team_id_teams",
                    "teams",
                    ["ao_team_id"],
                    ["id"],
                )


def _alter_tournament_categories(inspector: sa.Inspector) -> None:
    """Agrega bunkai_mode con default compatible."""
    if _has_column(inspector, "tournament_categories", "bunkai_mode"):
        return

    op.add_column(
        "tournament_categories",
        sa.Column(
            "bunkai_mode",
            sa.String(),
            nullable=False,
            server_default=sa.text("'NONE'"),
        ),
    )


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    _create_kata_tables(inspector)

    inspector = sa.inspect(bind)
    _alter_matches(inspector)

    inspector = sa.inspect(bind)
    _alter_tournament_categories(inspector)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_column(inspector, "tournament_categories", "bunkai_mode"):
        op.drop_column("tournament_categories", "bunkai_mode")

    inspector = sa.inspect(bind)
    has_aka_fk = _has_fk(inspector, "matches", "fk_matches_aka_team_id_teams")
    has_ao_fk = _has_fk(inspector, "matches", "fk_matches_ao_team_id_teams")
    if has_aka_fk or has_ao_fk:
        with op.batch_alter_table("matches", recreate="always") as batch_op:
            if has_aka_fk:
                batch_op.drop_constraint(
                    "fk_matches_aka_team_id_teams",
                    type_="foreignkey",
                )
            if has_ao_fk:
                batch_op.drop_constraint(
                    "fk_matches_ao_team_id_teams",
                    type_="foreignkey",
                )

    inspector = sa.inspect(bind)
    if _has_column(inspector, "matches", "bunkai_required"):
        op.drop_column("matches", "bunkai_required")
    if _has_column(inspector, "matches", "ao_team_id"):
        op.drop_column("matches", "ao_team_id")
    if _has_column(inspector, "matches", "aka_team_id"):
        op.drop_column("matches", "aka_team_id")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "kata_round_standings"):
        op.drop_index(
            op.f("ix_kata_round_standings_match_id"),
            table_name="kata_round_standings",
        )
        op.drop_table("kata_round_standings")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "kata_judge_scores"):
        op.drop_index(
            op.f("ix_kata_judge_scores_match_id"),
            table_name="kata_judge_scores",
        )
        op.drop_index(
            op.f("ix_kata_judge_scores_judge_id"),
            table_name="kata_judge_scores",
        )
        op.drop_table("kata_judge_scores")
