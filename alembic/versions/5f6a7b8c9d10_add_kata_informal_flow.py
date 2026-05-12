"""add kata informal flow mode and performance tables

Revision ID: 5f6a7b8c9d10
Revises: c80c22032ebc
Create Date: 2026-05-11 20:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "5f6a7b8c9d10"
down_revision: Union[str, Sequence[str], None] = "c80c22032ebc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    return column_name in columns


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "tournament_categories", "kata_flow_mode"):
        op.add_column(
            "tournament_categories",
            sa.Column(
                "kata_flow_mode",
                sa.String(),
                nullable=False,
                server_default=sa.text("'STANDARD'"),
            ),
        )
        op.execute(
            """
            UPDATE tournament_categories
            SET kata_flow_mode = 'STANDARD'
            WHERE kata_flow_mode IS NULL OR kata_flow_mode = ''
            """
        )

    if not _has_table(inspector, "kata_informal_performances"):
        op.create_table(
            "kata_informal_performances",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("category_id", sa.Integer(), nullable=False),
            sa.Column("athlete_id", sa.Integer(), nullable=False),
            sa.Column("sequence_number", sa.Integer(), nullable=False),
            sa.Column("performance_round", sa.Integer(), nullable=False),
            sa.Column(
                "status",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
            ),
            sa.Column("final_score", sa.Float(), nullable=False),
            sa.Column("kept_score_sum", sa.Float(), nullable=False),
            sa.Column("highest_score", sa.Float(), nullable=False),
            sa.Column("lowest_score", sa.Float(), nullable=False),
            sa.Column("max_judge_score", sa.Float(), nullable=False),
            sa.Column("is_extra_kata", sa.Boolean(), nullable=False),
            sa.Column("tiebreak_group", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
            sa.ForeignKeyConstraint(["category_id"], ["tournament_categories.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        with op.batch_alter_table("kata_informal_performances", schema=None) as batch_op:
            batch_op.create_index(
                batch_op.f("ix_kata_informal_performances_athlete_id"),
                ["athlete_id"],
                unique=False,
            )
            batch_op.create_index(
                batch_op.f("ix_kata_informal_performances_category_id"),
                ["category_id"],
                unique=False,
            )
            batch_op.create_index(
                "ix_kata_informal_performances_category_athlete",
                ["category_id", "athlete_id"],
                unique=False,
            )
            batch_op.create_index(
                "ix_kata_informal_performances_category_sequence",
                ["category_id", "sequence_number"],
                unique=False,
            )

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "kata_informal_judge_scores"):
        op.create_table(
            "kata_informal_judge_scores",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("performance_id", sa.Integer(), nullable=False),
            sa.Column("judge_id", sa.Integer(), nullable=False),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("slot_order", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["judge_id"],
                ["referees.id"],
            ),
            sa.ForeignKeyConstraint(
                ["performance_id"],
                ["kata_informal_performances.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "performance_id",
                "judge_id",
                name="uq_kata_informal_judge_scores_performance_judge",
            ),
        )
        with op.batch_alter_table("kata_informal_judge_scores", schema=None) as batch_op:
            batch_op.create_index(
                batch_op.f("ix_kata_informal_judge_scores_performance_id"),
                ["performance_id"],
                unique=False,
            )
            batch_op.create_index(
                batch_op.f("ix_kata_informal_judge_scores_judge_id"),
                ["judge_id"],
                unique=False,
            )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "kata_informal_judge_scores"):
        with op.batch_alter_table("kata_informal_judge_scores", schema=None) as batch_op:
            batch_op.drop_index(batch_op.f("ix_kata_informal_judge_scores_judge_id"))
            batch_op.drop_index(
                batch_op.f("ix_kata_informal_judge_scores_performance_id")
            )
        op.drop_table("kata_informal_judge_scores")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "kata_informal_performances"):
        with op.batch_alter_table("kata_informal_performances", schema=None) as batch_op:
            batch_op.drop_index("ix_kata_informal_performances_category_sequence")
            batch_op.drop_index("ix_kata_informal_performances_category_athlete")
            batch_op.drop_index(batch_op.f("ix_kata_informal_performances_category_id"))
            batch_op.drop_index(batch_op.f("ix_kata_informal_performances_athlete_id"))
        op.drop_table("kata_informal_performances")

    inspector = sa.inspect(bind)
    if _has_column(inspector, "tournament_categories", "kata_flow_mode"):
        op.drop_column("tournament_categories", "kata_flow_mode")
