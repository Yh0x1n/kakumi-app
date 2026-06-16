"""Tests for penalty escalation core service logic."""

import pytest
import reflex as rx
from kakumi_app.services.exceptions import AppError
from sqlmodel import select

from kakumi_app.models.tournament_model import (
    Match,
    MatchStatus,
    Participant,
    Penalty,
    PenaltyType,
)
from kakumi_app.services.kumite_scoring_service import apply_penalty


def _set_match_status(match_id: int, status: str) -> Match:
    """Set match status and return refreshed instance."""
    with rx.session() as session:
        match = session.get(Match, match_id)
        match.status = status
        session.add(match)
        session.commit()
        session.refresh(match)
        return match


def _penalties_for(match_id: int, participant: str) -> list[Penalty]:
    """Load penalties for one side ordered by creation."""
    with rx.session() as session:
        return session.exec(
            select(Penalty)
            .where(Penalty.match_id == match_id, Penalty.participant == participant)
            .order_by(Penalty.id)
        ).all()


def test_apply_c1_penalty(sample_match, db_session):
    """Applying first automatic penalty stores the first escalation step."""
    del db_session
    match = _set_match_status(sample_match.id, MatchStatus.IN_PROGRESS.value)

    with rx.session() as session:
        penalty = apply_penalty(
            session=session,
            match_id=match.id,
            participant=Participant.AKA.value,
        )

    assert penalty.penalty_type == "C1"
    penalties = _penalties_for(match.id, Participant.AKA.value)
    assert len(penalties) == 1
    assert penalties[0].penalty_type == "C1"


def test_escalation_c1_to_c2(sample_match, db_session):
    """Two automatic penalties escalate from C1 to C2."""
    del db_session
    match = _set_match_status(sample_match.id, MatchStatus.IN_PROGRESS.value)

    with rx.session() as session:
        apply_penalty(session, match.id, Participant.AKA.value)
    with rx.session() as session:
        second = apply_penalty(session, match.id, Participant.AKA.value)

    assert second.penalty_type == "C2"


def test_escalation_c2_to_c3(sample_match, db_session):
    """Third automatic penalty escalates to C3."""
    del db_session
    match = _set_match_status(sample_match.id, MatchStatus.IN_PROGRESS.value)

    with rx.session() as session:
        apply_penalty(session, match.id, Participant.AKA.value)
    with rx.session() as session:
        apply_penalty(session, match.id, Participant.AKA.value)
    with rx.session() as session:
        third = apply_penalty(session, match.id, Participant.AKA.value)

    assert third.penalty_type in {"C3", "HANSOKU_CHUI"}


def test_escalation_to_hansoku(sample_match, db_session):
    """Automatic chain reaches HANSOKU and ends the match."""
    del db_session
    match = _set_match_status(sample_match.id, MatchStatus.IN_PROGRESS.value)

    created: list[Penalty] = []
    for _ in range(5):
        with rx.session() as session:
            created.append(apply_penalty(session, match.id, Participant.AKA.value))

    assert [item.penalty_type for item in created] == [
        "C1",
        "C2",
        "C3",
        "HANSOKU_CHUI",
        "HANSOKU",
    ]

    with rx.session() as session:
        refreshed = session.get(Match, match.id)
        assert refreshed.status == MatchStatus.COMPLETED.value
        assert refreshed.winner_id == refreshed.ao_id


def test_penalty_type_recorded_correctly(sample_match, db_session):
    """Explicit penalty type bypasses escalation and is stored as-is."""
    del db_session
    match = _set_match_status(sample_match.id, MatchStatus.IN_PROGRESS.value)

    with rx.session() as session:
        penalty = apply_penalty(
            session=session,
            match_id=match.id,
            participant=Participant.AKA.value,
            penalty_type="C2",
        )

    assert penalty.penalty_type == "C2"


def test_apply_penalty_to_both_sides(sample_match, db_session):
    """AKA and AO maintain independent penalty chains."""
    del db_session
    match = _set_match_status(sample_match.id, MatchStatus.IN_PROGRESS.value)

    with rx.session() as session:
        aka_penalty = apply_penalty(session, match.id, Participant.AKA.value)
    with rx.session() as session:
        ao_penalty = apply_penalty(session, match.id, Participant.AO.value)

    assert aka_penalty.penalty_type == "C1"
    assert ao_penalty.penalty_type == "C1"
    assert len(_penalties_for(match.id, Participant.AKA.value)) == 1
    assert len(_penalties_for(match.id, Participant.AO.value)) == 1


def test_penalty_escalation_error_on_invalid_state(sample_match, db_session):
    """Applying penalty on non-IN_PROGRESS match raises escalation error."""
    del db_session
    match = _set_match_status(sample_match.id, MatchStatus.COMPLETED.value)

    with rx.session() as session:
        with pytest.raises(AppError):
            apply_penalty(
                session=session,
                match_id=match.id,
                participant=Participant.AKA.value,
            )


def test_undo_last_penalty_action_rolls_back_penalty_slot(sample_match, sample_user):
    """Undo de penalidad elimina último registro y vuelve slot previo."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_status(sample_match.id, MatchStatus.IN_PROGRESS.value)
    KumiteScoringService.apply_penalty(
        match_id=match.id,
        participant=Participant.AKA,
        penalty_type=PenaltyType.CHUI,
        reason="Primera",
        applied_by_id=sample_user.id,
    )
    second = KumiteScoringService.apply_penalty(
        match_id=match.id,
        participant=Participant.AKA,
        penalty_type=PenaltyType.CHUI,
        reason="Segunda",
        applied_by_id=sample_user.id,
    )
    assert second.penalty_type == PenaltyType.CHUI.value

    undo_result = KumiteScoringService.undo_last_action(match.id)
    assert undo_result.success is True

    penalties = _penalties_for(match.id, Participant.AKA.value)
    assert len(penalties) == 1
    assert penalties[-1].penalty_type == PenaltyType.CHUI.value
