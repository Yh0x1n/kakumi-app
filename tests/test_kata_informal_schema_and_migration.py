"""
Schema and migration tests for informal Kata models and category flow mode.

Merged from:
  - test_kata_informal_schema.py (class TestInMemorySchema)
  - test_kata_informal_migration.py (class TestMigrationSchema)
"""

from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import command
from sqlmodel import SQLModel, create_engine

from kakumi_app import models  # noqa: F401


def _get_schema_details() -> tuple[set[str], dict[str, set[str]], dict[str, set[str]]]:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    inspector = sa.inspect(engine)

    table_names = set(inspector.get_table_names())
    columns_by_table: dict[str, set[str]] = {}
    indexes_by_table: dict[str, set[str]] = {}
    for name in table_names:
        columns_by_table[name] = {col["name"] for col in inspector.get_columns(name)}
        indexes_by_table[name] = {
            idx["name"]
            for idx in inspector.get_indexes(name)
            if idx["name"] is not None
        }
    return table_names, columns_by_table, indexes_by_table


# =============================================================================
# In-memory schema tests — from test_kata_informal_schema.py
# =============================================================================


class TestInMemorySchema:
    """In-memory schema verification for informal Kata tables."""

    def test_informal_tables_exist(self) -> None:
        table_names, _, _ = _get_schema_details()
        assert "kata_informal_performances" in table_names
        assert "kata_informal_judge_scores" in table_names

    def test_informal_performance_required_columns(self) -> None:
        _, columns, _ = _get_schema_details()
        assert {
            "category_id",
            "athlete_id",
            "sequence_number",
            "performance_round",
            "final_score",
            "highest_score",
            "lowest_score",
            "max_judge_score",
            "is_extra_kata",
        }.issubset(columns["kata_informal_performances"])

    def test_tournament_category_contains_kata_flow_mode_column(self) -> None:
        _, columns, _ = _get_schema_details()
        assert "kata_flow_mode" in columns["tournament_categories"]

    def test_informal_indexes_exist(self) -> None:
        _, _, indexes = _get_schema_details()
        assert (
            "ix_kata_informal_performances_category_athlete"
            in indexes["kata_informal_performances"]
        )
        assert (
            "ix_kata_informal_performances_category_sequence"
            in indexes["kata_informal_performances"]
        )


# =============================================================================
# Migration round-trip tests — from test_kata_informal_migration.py
# =============================================================================


class TestMigrationSchema:
    """Alembic migration round-trip verification for informal Kata schema."""

    def test_informal_migration_upgrade_creates_tables_and_column(
        self,
        tmp_path: Path,
        alembic_config_for_db,
    ) -> None:
        """Head migration must create informal tables + kata_flow_mode column."""
        db_url = f"sqlite:///{tmp_path / 'kata_informal_upgrade.sqlite'}"
        config = alembic_config_for_db(db_url)

        command.upgrade(config, "head")

        engine = sa.create_engine(db_url)
        inspector = sa.inspect(engine)
        columns = {
            col["name"] for col in inspector.get_columns("tournament_categories")
        }
        tables = set(inspector.get_table_names())
        engine.dispose()

        assert "kata_flow_mode" in columns
        assert "kata_informal_performances" in tables
        assert "kata_informal_judge_scores" in tables

    def test_informal_migration_downgrade_removes_tables_and_column(
        self,
        tmp_path: Path,
        alembic_config_for_db,
    ) -> None:
        """Downgrade one revision should remove informal schema additions."""
        db_url = f"sqlite:///{tmp_path / 'kata_informal_downgrade.sqlite'}"
        config = alembic_config_for_db(db_url)

        command.upgrade(config, "head")
        command.downgrade(config, "c80c22032ebc")

        engine = sa.create_engine(db_url)
        inspector = sa.inspect(engine)
        columns = {
            col["name"] for col in inspector.get_columns("tournament_categories")
        }
        tables = set(inspector.get_table_names())
        engine.dispose()

        assert "kata_flow_mode" not in columns
        assert "kata_informal_performances" not in tables
        assert "kata_informal_judge_scores" not in tables
