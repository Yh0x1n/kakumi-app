"""remove match_action_logs add last_action_snapshot

Revision ID: 10577f633a38
Revises: b8d4e6f2a9c1
Create Date: 2026-06-15 21:37:03.418120

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "10577f633a38"
down_revision: Union[str, Sequence[str], None] = "b8d4e6f2a9c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Steps:
    1. Add last_action_snapshot column to matches table
    2. Copy the latest MatchActionLog.before_snapshot for each match
    3. Drop match_action_logs table
    """
    # 1. Add column first
    op.add_column(
        "matches",
        sa.Column(
            "last_action_snapshot",
            sa.String(length=65535),
            nullable=True,
        ),
    )

    # 2. Data migration: for each match, copy latest action log before_snapshot
    conn = op.get_bind()
    if conn.dialect.has_table(conn, "match_action_logs"):
        rows = conn.execute(
            sa.text(
                """
                SELECT mal.match_id, mal.before_snapshot
                FROM match_action_logs mal
                INNER JOIN (
                    SELECT match_id, MAX(id) AS max_id
                    FROM match_action_logs
                    GROUP BY match_id
                ) latest ON mal.id = latest.max_id
                """
            )
        ).fetchall()
        for match_id, before_snapshot in rows:
            conn.execute(
                sa.text(
                    "UPDATE matches SET last_action_snapshot = :snap WHERE id = :mid"
                ),
                {"snap": before_snapshot, "mid": match_id},
            )

    # 3. Drop indexes then table
    op.drop_index(
        op.f("ix_match_action_logs_action_kind"),
        table_name="match_action_logs",
    )
    op.drop_index(
        op.f("ix_match_action_logs_match_id"),
        table_name="match_action_logs",
    )
    op.drop_table("match_action_logs")


def downgrade() -> None:
    """Downgrade schema.

    Steps:
    1. Recreate match_action_logs table
    2. Restore data from matches.last_action_snapshot
    3. Drop matches.last_action_snapshot column
    """
    # 1. Recreate table
    op.create_table(
        "match_action_logs",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("match_id", sa.INTEGER(), nullable=False),
        sa.Column("applied_by_id", sa.INTEGER(), nullable=True),
        sa.Column("action_kind", sa.VARCHAR(length=50), nullable=False),
        sa.Column("participant", sa.VARCHAR(length=10), nullable=True),
        sa.Column("before_snapshot", sa.VARCHAR(), nullable=False),
        sa.Column("created_at", sa.DATETIME(), nullable=False),
        sa.ForeignKeyConstraint(
            ["applied_by_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["match_id"],
            ["matches.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_match_action_logs_match_id"),
        "match_action_logs",
        ["match_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_match_action_logs_action_kind"),
        "match_action_logs",
        ["action_kind"],
        unique=False,
    )

    # 2. Restore data from last_action_snapshot (best effort - recreates
    #    one action log per match that has a snapshot)
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, last_action_snapshot FROM matches WHERE last_action_snapshot IS NOT NULL"
        )
    ).fetchall()
    for match_id, snapshot in rows:
        conn.execute(
            sa.text(
                """
                INSERT INTO match_action_logs
                    (match_id, applied_by_id, action_kind, participant, before_snapshot, created_at)
                VALUES
                    (:mid, NULL, 'SNAPSHOT_MIGRATE', NULL, :snap, datetime('now'))
                """
            ),
            {"mid": match_id, "snap": snapshot},
        )

    # 3. Drop column
    op.drop_column("matches", "last_action_snapshot")
