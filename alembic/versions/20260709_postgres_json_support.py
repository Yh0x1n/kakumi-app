"""Migrate string JSON fields to sa.JSON (JSONB on PostgreSQL)

Revision ID: 20260709_postgres_json_support
Revises: 52613ac909db
Create Date: 2026-07-09

This migration marks 4 columns that changed from ``Optional[str]``
to ``sa.JSON`` in their model definitions:

- tournament_categories.third_place_ids
- referees.tatami_certified
- audit_logs.details
- tournament_event_logs.details

On PostgreSQL the column type is altered to JSONB with a safe cast.
On SQLite ``sa.JSON`` is stored as TEXT — ``alter_column`` is a no-op
for columns that already exist with the same logical type.
"""

from alembic import op
import sqlalchemy as sa

revision = "20260709_postgres_json_support"
down_revision = "52613ac909db"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name

    # tournament_categories.third_place_ids
    if dialect == "postgresql":
        op.alter_column(
            "tournament_categories", "third_place_ids",
            existing_type=sa.String(),
            type_=sa.JSON(),
            postgresql_using="third_place_ids::jsonb",
        )
    elif dialect == "sqlite":
        # No-op: sa.JSON maps to TEXT in SQLite, column already exists
        pass

    # referees.tatami_certified
    if dialect == "postgresql":
        op.alter_column(
            "referees", "tatami_certified",
            existing_type=sa.String(),
            type_=sa.JSON(),
            postgresql_using="tatami_certified::jsonb",
        )
    elif dialect == "sqlite":
        pass

    # audit_logs.details
    if dialect == "postgresql":
        op.alter_column(
            "audit_logs", "details",
            existing_type=sa.String(),
            type_=sa.JSON(),
            postgresql_using="details::jsonb",
        )
    elif dialect == "sqlite":
        pass

    # tournament_event_logs.details
    if dialect == "postgresql":
        op.alter_column(
            "tournament_event_logs", "details",
            existing_type=sa.String(),
            type_=sa.JSON(),
            postgresql_using="details::jsonb",
        )
    elif dialect == "sqlite":
        pass


def downgrade() -> None:
    # Revert JSON columns back to String.
    # On a fresh DB this is a no-op marker — no real data to revert.
    dialect = op.get_bind().dialect.name

    if dialect == "postgresql":
        op.alter_column(
            "tournament_categories", "third_place_ids",
            existing_type=sa.JSON(),
            type_=sa.String(),
            postgresql_using="third_place_ids::text",
        )
        op.alter_column(
            "referees", "tatami_certified",
            existing_type=sa.JSON(),
            type_=sa.String(),
            postgresql_using="tatami_certified::text",
        )
        op.alter_column(
            "audit_logs", "details",
            existing_type=sa.JSON(),
            type_=sa.String(),
            postgresql_using="details::text",
        )
        op.alter_column(
            "tournament_event_logs", "details",
            existing_type=sa.JSON(),
            type_=sa.String(),
            postgresql_using="details::text",
        )
    elif dialect == "sqlite":
        pass