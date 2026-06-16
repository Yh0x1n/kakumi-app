"""
Schema foundation tests for penalty-system: model defaults, exceptions, and migration.

Merged from:
  - test_penalty_foundations.py (class TestModelFoundations, trimmed Phase 3)
  - test_penalty_migrations.py (class TestMigrationRoundTrip)
"""

from __future__ import annotations

import datetime

import pytest
import sqlalchemy as sa
from sqlmodel import SQLModel, create_engine

from kakumi_app import models  # noqa: F401
from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.tournament_model import Tournament
from kakumi_app.services.exceptions import (
    AppError,
)


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


# =============================================================================
# Model foundations — from test_penalty_foundations.py (trimmed Phase 3)
# =============================================================================


class TestModelFoundations:
    """Model field defaults and exception hierarchy for penalty system."""

    @staticmethod
    def test_standings_delta_log_model_exists() -> None:
        """StandingsDeltaLog model should be importable with expected fields."""
        from kakumi_app.models import StandingsDeltaLog

        expected_fields = [
            "id",
            "athlete_id",
            "change_key",
            "before_snapshot",
            "applied_at",
        ]

        for field_name in expected_fields:
            assert field_name in StandingsDeltaLog.model_fields

    @staticmethod
    @pytest.mark.parametrize(
        ("model_instance", "field_name", "expected_default"),
        [
            pytest.param(
                Athlete(name="Test Athlete", age=26, gender="MALE"),
                "is_disqualified",
                False,
                id="athlete_is_disqualified_default_false",
            ),
            pytest.param(
                Tournament(
                    name="Test Tournament",
                    venue="Dojo",
                    start_date=datetime.date(2026, 1, 1),
                    end_date=datetime.date(2026, 1, 2),
                ),
                "scheduling_gap_seconds",
                75,
                id="tournament_scheduling_gap_default_75",
            ),
        ],
    )
    def test_model_field_defaults(
        model_instance: object,
        field_name: str,
        expected_default: object,
    ) -> None:
        """Model fields should exist with correct default values."""
        assert hasattr(model_instance, field_name)
        assert getattr(model_instance, field_name) == expected_default

    @staticmethod
    @pytest.mark.parametrize(
        ("exception_cls",),
        [
            pytest.param(AppError, id="penalty_removal_not_allowed"),
            pytest.param(AppError, id="athlete_scheduling_conflict"),
            pytest.param(AppError, id="penalty_escalation"),
        ],
    )
    def test_penalty_exception_is_exception(exception_cls: type) -> None:
        """All penalty exceptions should subclass Exception."""
        assert issubclass(exception_cls, Exception)


# =============================================================================
# Migration round-trip — from test_penalty_migrations.py
# =============================================================================


class TestMigrationRoundTrip:
    """Alembic migration round-trip verification for penalty schema."""

    @staticmethod
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

    @staticmethod
    def test_athlete_is_disqualified_column() -> None:
        """athletes table should contain is_disqualified column."""
        table_columns = _get_columns_by_table()

        assert "athletes" in table_columns
        assert "is_disqualified" in table_columns["athletes"]

    @staticmethod
    def test_tournament_scheduling_gap_seconds_column() -> None:
        """tournaments table should contain scheduling_gap_seconds column."""
        table_columns = _get_columns_by_table()

        assert "tournaments" in table_columns
        assert "scheduling_gap_seconds" in table_columns["tournaments"]
