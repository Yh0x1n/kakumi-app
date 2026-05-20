"""Tests for SHIKKAKU snapshot auditing and revert flow."""

import datetime
import json

import pytest
import reflex as rx
from sqlmodel import Session, select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.referee_model import Referee
from kakumi_app.models.tournament_model import (
    CompetitionSystem,
    Match,
    MatchStatus,
    MatchType,
    Modality,
    Penalty,
    Participant,
    PenaltyType,
    StandingsDeltaLog,
    Tournament,
    TournamentCategory,
    TournamentStatus,
)
from kakumi_app.services.exceptions import ShikkakuRevertError
from kakumi_app.services.kumite_scoring_service import apply_penalty, revert_shikkaku


def _create_tournament(session: Session, name: str) -> Tournament:
    """Create and persist a tournament."""
    tournament = Tournament(
        name=name,
        venue="Dojo Central",
        start_date=datetime.date(2026, 7, 1),
        end_date=datetime.date(2026, 7, 2),
        status=TournamentStatus.PLANIFICADO.value,
        tatami_count=2,
        is_public=True,
    )
    session.add(tournament)
    session.commit()
    session.refresh(tournament)
    return tournament


def _create_category(
    session: Session,
    tournament_id: int,
    modality: str,
    competition_system: str,
) -> TournamentCategory:
    """Create and persist a category."""
    category = TournamentCategory(
        name=f"{modality}-{competition_system}",
        modality=modality,
        competition_system=competition_system,
        tournament_id=tournament_id,
    )
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


def _create_referee(session: Session) -> Referee:
    """Create referee used by penalty writes."""
    referee = Referee(
        name="Ref One",
        license_number="REF-001",
        license_level="INTERNATIONAL",
        role="REFEREE",
        is_available=True,
    )
    session.add(referee)
    session.commit()
    session.refresh(referee)
    return referee


def _create_athlete(session: Session, name: str, suffix: str) -> Athlete:
    """Create and persist one athlete."""
    athlete = Athlete(
        name=name,
        age=26,
        gender="MALE",
        email=f"{suffix}@test.dev",
        belt_rank="Negro",
        is_active=True,
    )
    session.add(athlete)
    session.commit()
    session.refresh(athlete)
    return athlete


def _create_match(
    session: Session,
    category_id: int,
    referee_id: int,
    match_number: int,
    status: str,
    aka_id: int,
    ao_id: int,
    aka_score: int = 0,
    ao_score: int = 0,
    winner_id: int | None = None,
) -> Match:
    """Create and persist one RR match."""
    match = Match(
        round=1,
        match_number=match_number,
        position=match_number,
        match_type=MatchType.ROUND_ROBIN.value,
        category_id=category_id,
        aka_id=aka_id,
        ao_id=ao_id,
        aka_score=aka_score,
        ao_score=ao_score,
        winner_id=winner_id,
        status=status,
        start_time=datetime.datetime(2026, 7, 1, 10, 0)
        + datetime.timedelta(minutes=match_number),
        referee_id=referee_id,
    )
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


@pytest.fixture
def rr_fixture(in_memory_session: Session) -> dict[str, int]:
    """Create RR setup where SHIKKAKU happens before athlete's last bout."""
    tournament = _create_tournament(in_memory_session, "RR Revert")
    referee = _create_referee(in_memory_session)
    category = _create_category(
        in_memory_session,
        tournament.id,
        Modality.KUMITE_INDIVIDUAL.value,
        CompetitionSystem.ROUND_ROBIN.value,
    )
    dq_athlete = _create_athlete(in_memory_session, "DQ Athlete", "dq-athlete")
    opp_1 = _create_athlete(in_memory_session, "Opponent One", "opp-1")
    opp_2 = _create_athlete(in_memory_session, "Opponent Two", "opp-2")
    opp_3 = _create_athlete(in_memory_session, "Opponent Three", "opp-3")

    previous = _create_match(
        in_memory_session,
        category.id,
        referee.id,
        match_number=1,
        status=MatchStatus.COMPLETED.value,
        aka_id=dq_athlete.id,
        ao_id=opp_1.id,
        aka_score=4,
        ao_score=1,
        winner_id=dq_athlete.id,
    )
    current = _create_match(
        in_memory_session,
        category.id,
        referee.id,
        match_number=2,
        status=MatchStatus.IN_PROGRESS.value,
        aka_id=dq_athlete.id,
        ao_id=opp_2.id,
    )
    remaining = _create_match(
        in_memory_session,
        category.id,
        referee.id,
        match_number=3,
        status=MatchStatus.PENDING.value,
        aka_id=dq_athlete.id,
        ao_id=opp_3.id,
    )

    return {
        "tournament_id": tournament.id,
        "athlete_id": dq_athlete.id,
        "previous_match_id": previous.id,
        "current_match_id": current.id,
        "remaining_match_id": remaining.id,
    }


def _apply_shikkaku_non_last(change_data: dict[str, int]) -> str:
    """Apply SHIKKAKU in the non-last RR bout and return change key."""
    with rx.session() as session:
        apply_penalty(
            session=session,
            match_id=change_data["current_match_id"],
            participant=Participant.AKA.value,
            penalty_type=PenaltyType.SHIKKAKU,
        )

    return f"shikkaku-match-{change_data['current_match_id']}"


def test_standings_delta_log_written_on_shikkaku(rr_fixture: dict[str, int]) -> None:
    """SHIKKAKU non-last RR must write one standings delta log row."""
    change_key = _apply_shikkaku_non_last(rr_fixture)

    with rx.session() as session:
        log_row = session.exec(
            select(StandingsDeltaLog).where(StandingsDeltaLog.change_key == change_key)
        ).first()

        assert log_row is not None
        assert log_row.change_key == change_key
        assert log_row.before_snapshot
        assert log_row.athlete_id == rr_fixture["athlete_id"]
        assert log_row.tournament_id == rr_fixture["tournament_id"]


def test_before_snapshot_is_valid_json(rr_fixture: dict[str, int]) -> None:
    """Snapshot must be valid JSON payload."""
    change_key = _apply_shikkaku_non_last(rr_fixture)

    with rx.session() as session:
        log_row = session.exec(
            select(StandingsDeltaLog).where(StandingsDeltaLog.change_key == change_key)
        ).first()
        assert log_row is not None

        decoded = json.loads(log_row.before_snapshot)

        assert isinstance(decoded, (list, dict))


def test_before_snapshot_contains_prior_scores(rr_fixture: dict[str, int]) -> None:
    """Snapshot must contain score values from completed bout before nullify."""
    _apply_shikkaku_non_last(rr_fixture)

    with rx.session() as session:
        log_row = session.exec(select(StandingsDeltaLog)).first()
        assert log_row is not None

        snapshot = json.loads(log_row.before_snapshot)
        previous_entry = next(
            item
            for item in snapshot
            if item["match_id"] == rr_fixture["previous_match_id"]
        )

        assert previous_entry["aka_score"] == 4
        assert previous_entry["ao_score"] == 1


def test_revert_shikkaku_restores_scores(rr_fixture: dict[str, int]) -> None:
    """Revert must restore nullified scores and clear disqualification flag."""
    change_key = _apply_shikkaku_non_last(rr_fixture)

    with rx.session() as session:
        revert_shikkaku(session=session, change_key=change_key)

    with rx.session() as session:
        previous = session.get(Match, rr_fixture["previous_match_id"])
        remaining = session.get(Match, rr_fixture["remaining_match_id"])
        athlete = session.get(Athlete, rr_fixture["athlete_id"])

        assert previous is not None
        assert remaining is not None
        assert athlete is not None
        assert previous.aka_score == 4
        assert previous.ao_score == 1
        assert remaining.status == MatchStatus.PENDING.value
        assert athlete.is_disqualified is False


def test_revert_shikkaku_removes_delta_log(rr_fixture: dict[str, int]) -> None:
    """Revert must delete the consumed standings delta log row."""
    change_key = _apply_shikkaku_non_last(rr_fixture)

    with rx.session() as session:
        revert_shikkaku(session=session, change_key=change_key)

    with rx.session() as session:
        deleted = session.exec(
            select(StandingsDeltaLog).where(StandingsDeltaLog.change_key == change_key)
        ).first()
        assert deleted is None


def test_revert_shikkaku_missing_key_raises() -> None:
    """Revert must fail when change key is missing."""
    with rx.session() as session:
        with pytest.raises(ShikkakuRevertError):
            revert_shikkaku(session=session, change_key="nonexistent-key")


def test_revert_shikkaku_deletes_penalty_row(rr_fixture: dict[str, int]) -> None:
    """revert_shikkaku() must delete the SHIKKAKU Penalty row."""
    change_key = _apply_shikkaku_non_last(rr_fixture)

    with rx.session() as session:
        created_penalty = session.exec(
            select(Penalty).where(
                Penalty.match_id == rr_fixture["current_match_id"],
                Penalty.penalty_type == PenaltyType.SHIKKAKU.value,
            )
        ).first()
        assert created_penalty is not None

        revert_shikkaku(session=session, change_key=change_key)

    with rx.session() as session:
        deleted_penalty = session.exec(
            select(Penalty).where(
                Penalty.match_id == rr_fixture["current_match_id"],
                Penalty.penalty_type == PenaltyType.SHIKKAKU.value,
            )
        ).first()
        assert deleted_penalty is None
