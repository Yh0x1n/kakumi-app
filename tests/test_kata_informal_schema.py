"""Schema tests for informal Kata models and category flow mode."""

from __future__ import annotations

import sqlalchemy as sa
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
        indexes_by_table[name] = {idx["name"] for idx in inspector.get_indexes(name)}
    return table_names, columns_by_table, indexes_by_table


def test_informal_tables_exist() -> None:
    table_names, _, _ = _get_schema_details()
    assert "kata_informal_performances" in table_names
    assert "kata_informal_judge_scores" in table_names


def test_informal_performance_required_columns() -> None:
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


def test_tournament_category_contains_kata_flow_mode_column() -> None:
    _, columns, _ = _get_schema_details()
    assert "kata_flow_mode" in columns["tournament_categories"]


def test_informal_indexes_exist() -> None:
    _, _, indexes = _get_schema_details()
    assert "ix_kata_informal_performances_category_athlete" in indexes[
        "kata_informal_performances"
    ]
    assert "ix_kata_informal_performances_category_sequence" in indexes[
        "kata_informal_performances"
    ]
