"""Tests for athlete scheduling overlap enforcement."""

import datetime

import pytest
from sqlmodel import Session

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.tournament_model import (
    Match,
    MatchStatus,
    Modality,
    Tatami,
    Tournament,
    TournamentCategory,
    TournamentStatus,
)
from kakumi_app.services.exceptions import AthleteSchedulingConflictError
from kakumi_app.services.scheduling_service import check_athlete_scheduling_overlap


def _create_athlete(session: Session, name: str, suffix: str) -> Athlete:
    """Create one athlete for scheduling tests."""
    athlete = Athlete(
        name=name,
        age=25,
        gender="MALE",
        email=f"{suffix}@test.dev",
        belt_rank="Negro",
        is_active=True,
    )
    session.add(athlete)
    session.commit()
    session.refresh(athlete)
    return athlete


def _create_tournament(session: Session, gap_seconds: int = 75) -> Tournament:
    """Create one tournament with configurable scheduling gap."""
    tournament = Tournament(
        name=f"Sched Tournament {gap_seconds}",
        venue="Dojo",
        start_date=datetime.date(2026, 8, 1),
        end_date=datetime.date(2026, 8, 1),
        status=TournamentStatus.PLANIFICADO.value,
        tatami_count=2,
        scheduling_gap_seconds=gap_seconds,
    )
    session.add(tournament)
    session.commit()
    session.refresh(tournament)
    return tournament


def _create_category(session: Session, tournament_id: int) -> TournamentCategory:
    """Create one Kumite category with 3-minute match duration."""
    category = TournamentCategory(
        name="Kumite Individual",
        modality=Modality.KUMITE_INDIVIDUAL.value,
        tournament_id=tournament_id,
        match_duration_seconds=180,
    )
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


def _create_tatami(session: Session, tournament_id: int, name: str) -> Tatami:
    """Create one tatami for scheduling tests."""
    tatami = Tatami(name=name, tournament_id=tournament_id)
    session.add(tatami)
    session.commit()
    session.refresh(tatami)
    return tatami


def _create_match(
    session: Session,
    *,
    category_id: int,
    athlete_id: int,
    opponent_id: int,
    tatami_id: int,
    start_time: datetime.datetime | None,
) -> Match:
    """Create one match for a target athlete."""
    match = Match(
        round=1,
        match_number=1,
        position=0,
        category_id=category_id,
        aka_id=athlete_id,
        ao_id=opponent_id,
        tatami_id=tatami_id,
        start_time=start_time,
        status=MatchStatus.IN_PROGRESS.value,
    )
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


def test_overlap_detected_within_gap(in_memory_session: Session) -> None:
    """Raise conflict when same athlete has overlapping tatami windows."""
    athlete = _create_athlete(in_memory_session, "Shared Athlete", "athlete")
    opponent_a = _create_athlete(in_memory_session, "Opponent A", "opp-a")
    opponent_b = _create_athlete(in_memory_session, "Opponent B", "opp-b")
    tournament = _create_tournament(in_memory_session)
    category = _create_category(in_memory_session, tournament.id)
    tatami_a = _create_tatami(in_memory_session, tournament.id, "Tatami A")
    tatami_b = _create_tatami(in_memory_session, tournament.id, "Tatami B")

    _create_match(
        in_memory_session,
        category_id=category.id,
        athlete_id=athlete.id,
        opponent_id=opponent_a.id,
        tatami_id=tatami_a.id,
        start_time=datetime.datetime(2026, 8, 1, 10, 0, 0),
    )
    target_match = _create_match(
        in_memory_session,
        category_id=category.id,
        athlete_id=athlete.id,
        opponent_id=opponent_b.id,
        tatami_id=tatami_b.id,
        start_time=datetime.datetime(2026, 8, 1, 10, 2, 0),
    )

    with pytest.raises(AthleteSchedulingConflictError):
        check_athlete_scheduling_overlap(
            session=in_memory_session,
            athlete_id=athlete.id,
            match_id=target_match.id,
            gap_seconds=75,
        )


def test_no_overlap_outside_gap(in_memory_session: Session) -> None:
    """Do not raise when next match is outside duration+gap window."""
    athlete = _create_athlete(in_memory_session, "Gap Athlete", "gap-athlete")
    opponent_a = _create_athlete(in_memory_session, "Gap Opp A", "gap-opp-a")
    opponent_b = _create_athlete(in_memory_session, "Gap Opp B", "gap-opp-b")
    tournament = _create_tournament(in_memory_session)
    category = _create_category(in_memory_session, tournament.id)
    tatami_a = _create_tatami(in_memory_session, tournament.id, "Tatami A")
    tatami_b = _create_tatami(in_memory_session, tournament.id, "Tatami B")

    _create_match(
        in_memory_session,
        category_id=category.id,
        athlete_id=athlete.id,
        opponent_id=opponent_a.id,
        tatami_id=tatami_a.id,
        start_time=datetime.datetime(2026, 8, 1, 10, 0, 0),
    )
    target_match = _create_match(
        in_memory_session,
        category_id=category.id,
        athlete_id=athlete.id,
        opponent_id=opponent_b.id,
        tatami_id=tatami_b.id,
        start_time=datetime.datetime(2026, 8, 1, 10, 10, 0),
    )

    check_athlete_scheduling_overlap(
        session=in_memory_session,
        athlete_id=athlete.id,
        match_id=target_match.id,
        gap_seconds=75,
    )


def test_no_start_time_skips_check(in_memory_session: Session) -> None:
    """Skip overlap checks when target match has no start time."""
    athlete = _create_athlete(in_memory_session, "No Start Athlete", "nostart-athlete")
    opponent_a = _create_athlete(in_memory_session, "No Start Opp A", "nostart-opp-a")
    opponent_b = _create_athlete(in_memory_session, "No Start Opp B", "nostart-opp-b")
    tournament = _create_tournament(in_memory_session)
    category = _create_category(in_memory_session, tournament.id)
    tatami_a = _create_tatami(in_memory_session, tournament.id, "Tatami A")
    tatami_b = _create_tatami(in_memory_session, tournament.id, "Tatami B")

    _create_match(
        in_memory_session,
        category_id=category.id,
        athlete_id=athlete.id,
        opponent_id=opponent_a.id,
        tatami_id=tatami_a.id,
        start_time=datetime.datetime(2026, 8, 1, 10, 0, 0),
    )
    target_match = _create_match(
        in_memory_session,
        category_id=category.id,
        athlete_id=athlete.id,
        opponent_id=opponent_b.id,
        tatami_id=tatami_b.id,
        start_time=None,
    )

    check_athlete_scheduling_overlap(
        session=in_memory_session,
        athlete_id=athlete.id,
        match_id=target_match.id,
        gap_seconds=75,
    )


def test_custom_gap_respected(in_memory_session: Session) -> None:
    """Respect custom configured gap values when evaluating conflicts."""
    athlete = _create_athlete(in_memory_session, "Custom Gap Athlete", "custom-athlete")
    opponent_a = _create_athlete(in_memory_session, "Custom Opp A", "custom-opp-a")
    opponent_b = _create_athlete(in_memory_session, "Custom Opp B", "custom-opp-b")
    tournament = _create_tournament(in_memory_session, gap_seconds=30)
    category = _create_category(in_memory_session, tournament.id)
    tatami_a = _create_tatami(in_memory_session, tournament.id, "Tatami A")
    tatami_b = _create_tatami(in_memory_session, tournament.id, "Tatami B")

    _create_match(
        in_memory_session,
        category_id=category.id,
        athlete_id=athlete.id,
        opponent_id=opponent_a.id,
        tatami_id=tatami_a.id,
        start_time=datetime.datetime(2026, 8, 1, 10, 0, 0),
    )
    target_match = _create_match(
        in_memory_session,
        category_id=category.id,
        athlete_id=athlete.id,
        opponent_id=opponent_b.id,
        tatami_id=tatami_b.id,
        start_time=datetime.datetime(2026, 8, 1, 10, 3, 31),
    )

    check_athlete_scheduling_overlap(
        session=in_memory_session,
        athlete_id=athlete.id,
        match_id=target_match.id,
        gap_seconds=30,
    )

    with pytest.raises(AthleteSchedulingConflictError):
        check_athlete_scheduling_overlap(
            session=in_memory_session,
            athlete_id=athlete.id,
            match_id=target_match.id,
            gap_seconds=300,
        )


def test_default_gap_is_75() -> None:
    """Tournament default scheduling gap is 75 seconds."""
    tournament = Tournament(
        name="Default Gap",
        venue="Dojo",
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 1, 1),
    )

    assert tournament.scheduling_gap_seconds == 75
