"""Foundation tests for penalty-system Batch 1."""

import datetime

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.tournament_model import Tournament


def test_athlete_has_is_disqualified() -> None:
    """Athlete should expose disqualification flag with False default."""
    athlete = Athlete(
        name="Foundation Athlete",
        date_of_birth=datetime.date(2000, 1, 1),
        gender="MALE",
    )

    assert hasattr(athlete, "is_disqualified")
    assert athlete.is_disqualified is False


def test_tournament_has_scheduling_gap_seconds() -> None:
    """Tournament should expose scheduling gap with 75-second default."""
    tournament = Tournament(
        name="Foundation Tournament",
        venue="Dojo",
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 1, 2),
    )

    assert hasattr(tournament, "scheduling_gap_seconds")
    assert tournament.scheduling_gap_seconds == 75


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


def test_exceptions_importable() -> None:
    """Penalty system exceptions should be importable from services module."""
    from kakumi_app.services.exceptions import (
        AthleteSchedulingConflictError,
        PenaltyEscalationError,
        PenaltyRemovalNotAllowedError,
    )

    assert PenaltyRemovalNotAllowedError is not None
    assert AthleteSchedulingConflictError is not None
    assert PenaltyEscalationError is not None


def test_penalty_removal_not_allowed_is_exception() -> None:
    """PenaltyRemovalNotAllowedError should subclass Exception."""
    from kakumi_app.services.exceptions import PenaltyRemovalNotAllowedError

    assert issubclass(PenaltyRemovalNotAllowedError, Exception)


def test_athlete_scheduling_conflict_is_exception() -> None:
    """AthleteSchedulingConflictError should subclass Exception."""
    from kakumi_app.services.exceptions import AthleteSchedulingConflictError

    assert issubclass(AthleteSchedulingConflictError, Exception)


def test_penalty_escalation_is_exception() -> None:
    """PenaltyEscalationError should subclass Exception."""
    from kakumi_app.services.exceptions import PenaltyEscalationError

    assert issubclass(PenaltyEscalationError, Exception)
