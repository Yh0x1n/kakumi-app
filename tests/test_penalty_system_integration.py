"""Integration scenarios for penalty-system batch 8."""

import datetime

import pytest
import reflex as rx
from sqlmodel import Session, select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.tournament_model import Match, MatchStatus, Participant, Penalty
from kakumi_app.models.tournament_model import PenaltyType
from kakumi_app.services.exceptions import (
    AthleteSchedulingConflictError,
    PenaltyRemovalNotAllowedError,
)
from kakumi_app.services.kumite_scoring_service import (
    apply_penalty,
    remove_last_penalty,
    revert_shikkaku,
)
from kakumi_app.services.scheduling_service import check_athlete_scheduling_overlap


def _set_match_status(session: Session, match_id: int, status: str) -> None:
    """Update one match status."""
    match = session.get(Match, match_id)
    assert match is not None
    match.status = status
    session.add(match)
    session.commit()


def _penalty_types_for_match_side(
    session: Session,
    match_id: int,
    participant: str,
) -> list[str]:
    """Load penalty types for one match side ordered by id."""
    penalties = session.exec(
        select(Penalty)
        .where(Penalty.match_id == match_id, Penalty.participant == participant)
        .order_by(Penalty.id)
    ).all()
    return [penalty.penalty_type for penalty in penalties]


def test_scenario_1_full_escalation_chain(rr_pool_fixture: dict[str, int]) -> None:
    """CHUI chain escalates to HANSOKU and ends match with opponent winner."""
    with rx.session() as session:
        _set_match_status(
            session,
            rr_pool_fixture["current_match_id"],
            MatchStatus.IN_PROGRESS.value,
        )

        created: list[str] = []
        for _ in range(5):
            penalty = apply_penalty(
                session=session,
                match_id=rr_pool_fixture["current_match_id"],
                participant=Participant.AKA.value,
            )
            created.append(penalty.penalty_type)

        refreshed = session.get(Match, rr_pool_fixture["current_match_id"])
        assert refreshed is not None
        assert created == ["C1", "C2", "C3", "HANSOKU_CHUI", "HANSOKU"]
        assert refreshed.status == MatchStatus.COMPLETED.value
        assert refreshed.winner_id == rr_pool_fixture["opponent_2_id"]


def test_scenario_2_shikkaku_last_rr_bout(rr_pool_fixture: dict[str, int]) -> None:
    """SHIKKAKU on athlete last RR bout keeps previous scores."""
    with rx.session() as session:
        # Move pool third match to completed so current is last remaining RR bout.
        _set_match_status(
            session,
            rr_pool_fixture["pool_match_id"],
            MatchStatus.COMPLETED.value,
        )
        _set_match_status(
            session,
            rr_pool_fixture["current_match_id"],
            MatchStatus.IN_PROGRESS.value,
        )

        apply_penalty(
            session=session,
            match_id=rr_pool_fixture["current_match_id"],
            participant=Participant.AKA.value,
            penalty_type=PenaltyType.SHIKKAKU,
        )

        previous = session.get(Match, rr_pool_fixture["previous_match_id"])
        current = session.get(Match, rr_pool_fixture["current_match_id"])
        dq_athlete = session.get(Athlete, rr_pool_fixture["dq_athlete_id"])

        assert previous is not None
        assert current is not None
        assert dq_athlete is not None
        assert previous.aka_score == 4
        assert previous.ao_score == 1
        assert current.status == MatchStatus.COMPLETED.value
        assert current.winner_id == rr_pool_fixture["opponent_2_id"]
        assert dq_athlete.is_disqualified is True


def test_scenario_3_shikkaku_not_last_rr_bout(
    rr_pool_fixture: dict[str, int],
) -> None:
    """SHIKKAKU non-last RR nullifies prior and cancels remaining bouts."""
    with rx.session() as session:
        remaining = Match(
            round=1,
            match_number=4,
            position=4,
            match_type="ROUND_ROBIN",
            category_id=rr_pool_fixture["category_id"],
            aka_id=rr_pool_fixture["dq_athlete_id"],
            ao_id=rr_pool_fixture["opponent_1_id"],
            status=MatchStatus.PENDING.value,
            referee_id=rr_pool_fixture["referee_id"],
            tatami_id=rr_pool_fixture["tatami_1_id"],
            start_time=datetime.datetime(2026, 9, 1, 10, 30, 0),
        )
        session.add(remaining)
        session.commit()
        session.refresh(remaining)

        _set_match_status(
            session,
            rr_pool_fixture["current_match_id"],
            MatchStatus.IN_PROGRESS.value,
        )

        apply_penalty(
            session=session,
            match_id=rr_pool_fixture["current_match_id"],
            participant=Participant.AKA.value,
            penalty_type=PenaltyType.SHIKKAKU,
        )

        previous = session.get(Match, rr_pool_fixture["previous_match_id"])
        current = session.get(Match, rr_pool_fixture["current_match_id"])
        future = session.get(Match, remaining.id)

        assert previous is not None
        assert current is not None
        assert future is not None
        assert previous.aka_score == 0
        assert previous.ao_score == 0
        assert current.status == MatchStatus.COMPLETED.value
        assert future.status == "CANCELLED"


def test_scenario_4_remove_penalty_completed_raises(
    rr_pool_fixture: dict[str, int],
) -> None:
    """remove_last_penalty must raise outside IN_PROGRESS status."""
    with rx.session() as session:
        _set_match_status(
            session,
            rr_pool_fixture["current_match_id"],
            MatchStatus.IN_PROGRESS.value,
        )
        apply_penalty(
            session=session,
            match_id=rr_pool_fixture["current_match_id"],
            participant=Participant.AKA.value,
            penalty_type=PenaltyType.CHUI,
        )
        _set_match_status(
            session,
            rr_pool_fixture["current_match_id"],
            MatchStatus.COMPLETED.value,
        )

        with pytest.raises(PenaltyRemovalNotAllowedError):
            remove_last_penalty(
                session=session,
                match_id=rr_pool_fixture["current_match_id"],
                participant=Participant.AKA.value,
            )


def test_scenario_5_scheduling_overlap_raises(
    in_memory_session: Session,
    tatami_fixture: dict[str, int],
) -> None:
    """Scheduling overlap check raises conflict for same athlete."""
    with pytest.raises(AthleteSchedulingConflictError):
        check_athlete_scheduling_overlap(
            session=in_memory_session,
            athlete_id=tatami_fixture["athlete_id"],
            match_id=tatami_fixture["target_match_id"],
            gap_seconds=75,
        )


def test_scenario_6_revert_shikkaku_restores(
    rr_pool_fixture: dict[str, int],
) -> None:
    """Apply SHIKKAKU then revert restores scores and DQ flag."""
    with rx.session() as session:
        remaining = Match(
            round=1,
            match_number=5,
            position=5,
            match_type="ROUND_ROBIN",
            category_id=rr_pool_fixture["category_id"],
            aka_id=rr_pool_fixture["dq_athlete_id"],
            ao_id=rr_pool_fixture["opponent_1_id"],
            status=MatchStatus.PENDING.value,
            referee_id=rr_pool_fixture["referee_id"],
            tatami_id=rr_pool_fixture["tatami_1_id"],
            start_time=datetime.datetime(2026, 9, 1, 10, 40, 0),
        )
        session.add(remaining)
        session.commit()
        session.refresh(remaining)

        _set_match_status(
            session,
            rr_pool_fixture["current_match_id"],
            MatchStatus.IN_PROGRESS.value,
        )

        apply_penalty(
            session=session,
            match_id=rr_pool_fixture["current_match_id"],
            participant=Participant.AKA.value,
            penalty_type=PenaltyType.SHIKKAKU,
        )
        revert_shikkaku(
            session=session,
            change_key=f"shikkaku-match-{rr_pool_fixture['current_match_id']}",
        )

        previous = session.get(Match, rr_pool_fixture["previous_match_id"])
        restored_future = session.get(Match, remaining.id)
        dq_athlete = session.get(Athlete, rr_pool_fixture["dq_athlete_id"])

        assert previous is not None
        assert restored_future is not None
        assert dq_athlete is not None
        assert previous.aka_score == 4
        assert previous.ao_score == 1
        assert restored_future.status == MatchStatus.PENDING.value
        assert dq_athlete.is_disqualified is False


def test_scenario_7_team_shikkaku(team_match_fixture: dict[str, object]) -> None:
    """SHIKKAKU team match disqualifies all athletes in penalized team."""
    with rx.session() as session:
        apply_penalty(
            session=session,
            match_id=int(team_match_fixture["match_id"]),
            participant=Participant.AKA.value,
            penalty_type=PenaltyType.SHIKKAKU,
        )

        for athlete_id in team_match_fixture["aka_athlete_ids"]:
            athlete = session.get(Athlete, int(athlete_id))
            assert athlete is not None
            assert athlete.is_disqualified is True

        for athlete_id in team_match_fixture["ao_athlete_ids"]:
            athlete = session.get(Athlete, int(athlete_id))
            assert athlete is not None
            assert athlete.is_disqualified is False


def test_scenario_8_direct_hansoku_chui(rr_pool_fixture: dict[str, int]) -> None:
    """Explicit direct HANSOKU_CHUI persists without accumulation."""
    with rx.session() as session:
        _set_match_status(
            session,
            rr_pool_fixture["current_match_id"],
            MatchStatus.IN_PROGRESS.value,
        )
        penalty = apply_penalty(
            session=session,
            match_id=rr_pool_fixture["current_match_id"],
            participant=Participant.AKA.value,
            penalty_type=PenaltyType.HANSOKU_CHUI,
        )

        penalty_types = _penalty_types_for_match_side(
            session=session,
            match_id=rr_pool_fixture["current_match_id"],
            participant=Participant.AKA.value,
        )
        assert penalty.penalty_type == PenaltyType.HANSOKU_CHUI.value
        assert penalty_types[-1] == PenaltyType.HANSOKU_CHUI.value
