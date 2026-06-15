"""Schema foundation tests for penalty-system Batch 1 models."""

import sqlalchemy as sa
from sqlmodel import SQLModel, create_engine

from kakumi_app import models  # noqa: F401


def _get_columns_by_table() -> dict[str, set[str]]:
    """Create in-memory schema and return table -> columns mapping."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    inspector = sa.inspect(engine)
    table_columns: dict[str, set[str]] = {}
    for table_name in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        table_columns[table_name] = columns

    return table_columns


def test_standings_delta_log_table_columns() -> None:
    """standings_delta_logs should include all expected columns."""
    table_columns = _get_columns_by_table()

    assert "standings_delta_logs" in table_columns
    assert {
        "id",
        "athlete_id",
        "change_key",
        "before_snapshot",
        "applied_at",
        "tournament_id",
    }.issubset(table_columns["standings_delta_logs"])


def test_athlete_is_disqualified_column() -> None:
    """athletes table should contain is_disqualified column."""
    table_columns = _get_columns_by_table()

    assert "athletes" in table_columns
    assert "is_disqualified" in table_columns["athletes"]


def test_tournament_scheduling_gap_seconds_column() -> None:
    """tournaments table should contain scheduling_gap_seconds column."""
    table_columns = _get_columns_by_table()

    assert "tournaments" in table_columns
    assert "scheduling_gap_seconds" in table_columns["tournaments"]
