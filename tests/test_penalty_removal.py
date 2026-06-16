"""Tests for remove_last_penalty guard and deletion behavior."""

import datetime

import pytest
import reflex as rx
from kakumi_app.services.exceptions import AppError
from sqlmodel import Session, select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.referee_model import Referee
from kakumi_app.models.tournament_model import (
    CompetitionSystem,
    Match,
    MatchStatus,
    MatchType,
    Modality,
    Participant,
    Penalty,
    PenaltyType,
    Tournament,
    TournamentCategory,
    TournamentStatus,
)
from kakumi_app.services.kumite_scoring_service import remove_last_penalty


def _create_athlete(session: Session, suffix: str) -> Athlete:
    """Create and persist one athlete for tests.

    Args:
        session: Active SQLModel session.
        suffix: Unique suffix for email and name.

    Returns:
        Persisted athlete instance.
    """
    athlete = Athlete(
        name=f"Athlete {suffix}",
        age=26,
        gender="MALE",
        email=f"athlete-{suffix}@test.dev",
        belt_rank="Negro",
        is_active=True,
    )
    session.add(athlete)
    session.commit()
    session.refresh(athlete)
    return athlete


def _create_match(session: Session, status: str) -> Match:
    """Create and persist one kumite match with desired status.

    Args:
        session: Active SQLModel session.
        status: Match status string.

    Returns:
        Persisted match entity.
    """
    tournament = Tournament(
        name=f"Penalty Removal {status}",
        venue="Dojo Central",
        start_date=datetime.date(2026, 7, 1),
        end_date=datetime.date(2026, 7, 2),
        status=TournamentStatus.PLANIFICADO.value,
        tatami_count=1,
        is_public=True,
    )
    session.add(tournament)
    session.commit()
    session.refresh(tournament)

    category = TournamentCategory(
        name=f"Kumite {status}",
        modality=Modality.KUMITE_INDIVIDUAL.value,
        competition_system=CompetitionSystem.ELIMINATION.value,
        tournament_id=tournament.id,
    )
    session.add(category)
    session.commit()
    session.refresh(category)

    referee = Referee(
        name="Ref Removal",
        license_number=f"REF-{status}",
        license_level="INTERNATIONAL",
        role="REFEREE",
        is_available=True,
    )
    session.add(referee)
    session.commit()
    session.refresh(referee)

    aka = _create_athlete(session, f"aka-{status.lower()}")
    ao = _create_athlete(session, f"ao-{status.lower()}")

    match = Match(
        round=1,
        match_number=1,
        position=1,
        match_type=MatchType.ELIMINATION.value,
        category_id=category.id,
        aka_id=aka.id,
        ao_id=ao.id,
        status=status,
        referee_id=referee.id,
        aka_score=0,
        ao_score=0,
    )
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


def _insert_penalty(
    session: Session,
    match_id: int,
    referee_id: int,
    participant: str,
    penalty_type: str,
) -> Penalty:
    """Insert one penalty row for setup.

    Args:
        session: Active SQLModel session.
        match_id: Match identifier.
        referee_id: Referee identifier.
        participant: Penalized side.
        penalty_type: Stored penalty type.

    Returns:
        Persisted penalty.
    """
    penalty = Penalty(
        match_id=match_id,
        given_by_id=referee_id,
        participant=participant,
        penalty_type=penalty_type,
        reason="SETUP",
        is_accumulated=False,
    )
    session.add(penalty)
    session.commit()
    session.refresh(penalty)
    return penalty


def _load_penalties(session: Session, match_id: int, participant: str) -> list[Penalty]:
    """Return penalties ordered by id ascending."""
    return session.exec(
        select(Penalty)
        .where(Penalty.match_id == match_id, Penalty.participant == participant)
        .order_by(Penalty.id)
    ).all()


def test_remove_last_penalty_in_progress(in_memory_session: Session) -> None:
    """IN_PROGRESS match can remove latest penalty without exception."""
    match = _create_match(in_memory_session, MatchStatus.IN_PROGRESS.value)
    first = _insert_penalty(
        in_memory_session,
        match.id,
        match.referee_id,
        Participant.AKA.value,
        PenaltyType.CHUI.value,
    )
    _insert_penalty(
        in_memory_session,
        match.id,
        match.referee_id,
        Participant.AKA.value,
        PenaltyType.CHUI.value,
    )

    with rx.session() as session:
        removed = remove_last_penalty(session, match.id, Participant.AKA.value)

    assert removed is not None

    with rx.session() as session:
        penalties = _load_penalties(session, match.id, Participant.AKA.value)
        assert len(penalties) == 1
        assert penalties[0].id == first.id


def test_remove_last_penalty_completed_raises(in_memory_session: Session) -> None:
    """COMPLETED match rejects penalty removal per WKF correction rule."""
    match = _create_match(in_memory_session, MatchStatus.COMPLETED.value)

    with rx.session() as session:
        with pytest.raises(AppError):
            remove_last_penalty(session, match.id, Participant.AKA.value)


def test_remove_last_penalty_disqualified_raises(in_memory_session: Session) -> None:
    """DISQUALIFIED match rejects penalty removal."""
    match = _create_match(in_memory_session, MatchStatus.DISQUALIFIED.value)

    with rx.session() as session:
        with pytest.raises(AppError):
            remove_last_penalty(session, match.id, Participant.AKA.value)


def test_remove_last_penalty_no_penalties_raises(in_memory_session: Session) -> None:
    """Removing with zero penalties raises a value error."""
    match = _create_match(in_memory_session, MatchStatus.IN_PROGRESS.value)

    with rx.session() as session:
        with pytest.raises(ValueError, match="No penalties to remove"):
            remove_last_penalty(session, match.id, Participant.AKA.value)


def test_remove_last_penalty_deescalates_hansoku_chui(
    in_memory_session: Session,
) -> None:
    """Removing latest HANSOKU_CHUI leaves prior CHUI chain intact."""
    match = _create_match(in_memory_session, MatchStatus.IN_PROGRESS.value)
    _insert_penalty(
        in_memory_session,
        match.id,
        match.referee_id,
        Participant.AKA.value,
        PenaltyType.CHUI.value,
    )
    _insert_penalty(
        in_memory_session,
        match.id,
        match.referee_id,
        Participant.AKA.value,
        PenaltyType.CHUI.value,
    )
    _insert_penalty(
        in_memory_session,
        match.id,
        match.referee_id,
        Participant.AKA.value,
        PenaltyType.CHUI.value,
    )
    last = _insert_penalty(
        in_memory_session,
        match.id,
        match.referee_id,
        Participant.AKA.value,
        PenaltyType.HANSOKU_CHUI.value,
    )

    with rx.session() as session:
        removed = remove_last_penalty(session, match.id, Participant.AKA.value)

    assert removed.id == last.id
    assert removed.penalty_type == PenaltyType.HANSOKU_CHUI.value

    with rx.session() as session:
        penalties = _load_penalties(session, match.id, Participant.AKA.value)
        assert len(penalties) == 3
        assert all(item.penalty_type == PenaltyType.CHUI.value for item in penalties)


def test_remove_last_penalty_returns_removed_penalty(
    in_memory_session: Session,
) -> None:
    """Service returns deleted penalty object to caller."""
    match = _create_match(in_memory_session, MatchStatus.IN_PROGRESS.value)
    inserted = _insert_penalty(
        in_memory_session,
        match.id,
        match.referee_id,
        Participant.AKA.value,
        PenaltyType.CHUI.value,
    )

    with rx.session() as session:
        removed = remove_last_penalty(session, match.id, Participant.AKA.value)

    assert removed.id == inserted.id
    assert removed.match_id == match.id
    assert removed.participant == Participant.AKA.value
