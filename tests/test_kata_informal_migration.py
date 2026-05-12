"""Migration tests for informal Kata schema rollout."""

from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import command


def test_informal_migration_upgrade_creates_tables_and_column(
    tmp_path: Path,
    alembic_config_for_db,
) -> None:
    """Head migration must create informal tables + kata_flow_mode column."""
    db_url = f"sqlite:///{tmp_path / 'kata_informal_upgrade.sqlite'}"
    config = alembic_config_for_db(db_url)

    command.upgrade(config, "head")

    engine = sa.create_engine(db_url)
    inspector = sa.inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("tournament_categories")}
    tables = set(inspector.get_table_names())
    engine.dispose()

    assert "kata_flow_mode" in columns
    assert "kata_informal_performances" in tables
    assert "kata_informal_judge_scores" in tables


def test_informal_migration_downgrade_removes_tables_and_column(
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
    columns = {col["name"] for col in inspector.get_columns("tournament_categories")}
    tables = set(inspector.get_table_names())
    engine.dispose()

    assert "kata_flow_mode" not in columns
    assert "kata_informal_performances" not in tables
    assert "kata_informal_judge_scores" not in tables
