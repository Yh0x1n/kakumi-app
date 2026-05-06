"""Tests for KumiteMatchState penalty/timer synchronization."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import reflex as rx
from sqlmodel import select

from kakumi_app.models.tournament_model import (
    Match,
    MatchActionLog,
    MatchStatus,
    Participant,
    Penalty,
    PenaltyType,
    ScoreType,
)
from kakumi_app.services.kumite_scoring_service import KumiteScoringService
from kakumi_app.services.exceptions import (
    AthleteSchedulingConflictError,
    PenaltyRemovalNotAllowedError,
)
from kakumi_app.states.kumite_match_state import KumiteMatchState


def _collect_public_state_vars(state: KumiteMatchState) -> dict[str, object]:
    """Collect public vars declared in state class.

    Args:
        state: State instance under test.

    Returns:
        Mapping from var name to current value.
    """
    public_annotations = {
        key: value
        for key, value in state.__class__.__annotations__.items()
        if not key.startswith("_")
    }
    return {name: getattr(state, name) for name in public_annotations}


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_timer_pauses_before_penalty_submit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Timer pauses before backend penalty call starts."""
    state = KumiteMatchState()
    state.match_id = 77

    def _apply_penalty(*, session, match_id, participant, penalty_type):
        del session
        assert match_id == 77
        assert participant == "AKA"
        assert penalty_type is None
        assert state.timer_paused is True
        return SimpleNamespace(penalty_type=PenaltyType.CHUI.value)

    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.kumite_scoring_service.apply_penalty",
        _apply_penalty,
    )

    events = [
        event async for event in state.apply_penalty_cumulative(participant="AKA")
    ]
    assert events == []


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_timer_resumes_after_penalty_submit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Timer resumes after successful backend call."""
    state = KumiteMatchState()
    state.match_id = 42

    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.kumite_scoring_service.apply_penalty",
        lambda **kwargs: SimpleNamespace(penalty_type=PenaltyType.CHUI.value),
    )

    events = [
        event async for event in state.apply_penalty_cumulative(participant="AKA")
    ]
    assert events == []
    assert state.timer_paused is False


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_apply_penalty_cumulative_calls_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cumulative handler calls service with penalty_type=None."""
    state = KumiteMatchState()
    state.match_id = 99

    mock_apply_penalty = Mock(
        return_value=SimpleNamespace(penalty_type=PenaltyType.CHUI.value)
    )
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.kumite_scoring_service.apply_penalty",
        mock_apply_penalty,
    )

    events = [event async for event in state.apply_penalty_cumulative(participant="AO")]
    assert events == []

    mock_apply_penalty.assert_called_once()
    call_kwargs = mock_apply_penalty.call_args.kwargs
    assert call_kwargs["match_id"] == 99
    assert call_kwargs["participant"] == "AO"
    assert call_kwargs["penalty_type"] is None


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_apply_penalty_direct_passes_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Direct mode maps string to PenaltyType enum for service call."""
    state = KumiteMatchState()
    state.match_id = 11

    mock_apply_penalty = Mock(
        return_value=SimpleNamespace(penalty_type=PenaltyType.HANSOKU_CHUI.value)
    )
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.kumite_scoring_service.apply_penalty",
        mock_apply_penalty,
    )

    events = [
        event
        async for event in state.apply_penalty_direct(
            participant="AKA",
            penalty_type="HANSOKU_CHUI",
        )
    ]
    assert events == []

    mock_apply_penalty.assert_called_once()
    call_kwargs = mock_apply_penalty.call_args.kwargs
    assert call_kwargs["match_id"] == 11
    assert call_kwargs["participant"] == "AKA"
    assert call_kwargs["penalty_type"] == PenaltyType.HANSOKU_CHUI


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_scheduling_conflict_shows_toast(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scheduling conflict surfaces error feedback to operator."""
    state = KumiteMatchState()
    state.match_id = 17

    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.kumite_scoring_service.apply_penalty",
        Mock(side_effect=AthleteSchedulingConflictError("Tatami overlap detected")),
    )

    toast_error = Mock(return_value="toast-error")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.error", toast_error
    )

    events = [
        event async for event in state.apply_penalty_cumulative(participant="AKA")
    ]

    assert state.error_message == "Tatami overlap detected"
    assert state.timer_paused is False
    assert events == ["toast-error"]
    toast_error.assert_called_once_with("Tatami overlap detected")


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_remove_penalty_guard_shows_toast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Removal guard error surfaces toast/error state."""
    state = KumiteMatchState()
    state.match_id = 23

    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.kumite_scoring_service.remove_last_penalty",
        Mock(
            side_effect=PenaltyRemovalNotAllowedError(
                "Penalty removal only allowed when match is IN_PROGRESS"
            )
        ),
    )

    toast_error = Mock(return_value="toast-removal")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.error", toast_error
    )

    events = [event async for event in state.remove_last_penalty(participant="AO")]

    assert (
        state.error_message == "Penalty removal only allowed when match is IN_PROGRESS"
    )
    assert state.timer_paused is False
    assert events == ["toast-removal"]
    toast_error.assert_called_once_with(
        "Penalty removal only allowed when match is IN_PROGRESS"
    )


def test_state_vars_are_json_serializable() -> None:
    """All public state vars are JSON-serializable types."""
    state = KumiteMatchState()
    public_vars = _collect_public_state_vars(state)

    assert public_vars
    for key, value in public_vars.items():
        try:
            json.dumps(value)
        except TypeError as error:  # pragma: no cover - explicit failure detail
            pytest.fail(f"State var '{key}' is not JSON serializable: {error}")


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_sync_from_match_updates_scoreboard_vars(
    sample_match,
    sample_user,
) -> None:
    """State sync loads names, scores, senshu and penalty slots from DB truth."""
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        session.add(match)
        session.commit()

    KumiteScoringService.apply_score(
        match_id=sample_match.id,
        participant=Participant.AKA,
        score_type=ScoreType.YUKO,
        applied_by_id=sample_user.id,
    )
    KumiteScoringService.apply_penalty(
        match_id=sample_match.id,
        participant=Participant.AKA,
        penalty_type=PenaltyType.CHUI,
        reason="C1",
        applied_by_id=sample_user.id,
    )
    KumiteScoringService.apply_penalty(
        match_id=sample_match.id,
        participant=Participant.AKA,
        penalty_type=PenaltyType.HANSOKU_CHUI,
        reason="C2",
        applied_by_id=sample_user.id,
    )

    state = KumiteMatchState()
    with rx.session() as session:
        state._sync_from_match(session=session, match_id=sample_match.id)

    assert state.has_active_match is True
    assert state.is_exhibition_mode is False
    assert state.match_id == sample_match.id
    assert state.aka_score == 1
    assert state.ao_score == 0
    assert state.aka_name == "Carlos Martinez"
    assert state.ao_name == "Ana Rodriguez"
    assert state.aka_senshu is True
    assert state.ao_senshu is False
    assert state.aka_penalty_slots == {
        "C1": True,
        "C2": True,
        "C3": True,
        "HC": True,
        "H": False,
    }
    assert state.ao_penalty_slots == {
        "C1": False,
        "C2": False,
        "C3": False,
        "HC": False,
        "H": False,
    }


@pytest.mark.asyncio
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("chui_count", "expected_slots"),
    [
        (
            2,
            {
                "C1": True,
                "C2": True,
                "C3": False,
                "HC": False,
                "H": False,
            },
        ),
        (
            3,
            {
                "C1": True,
                "C2": True,
                "C3": True,
                "HC": False,
                "H": False,
            },
        ),
    ],
)
async def test_sync_from_match_treats_chui_count_as_c1_c2_c3_equivalent(
    sample_match,
    sample_user,
    chui_count: int,
    expected_slots: dict[str, bool],
) -> None:
    """Legacy CHUI rows map to progressive C1/C2/C3 scoreboard slots."""
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        session.add(match)
        session.commit()

    for i in range(chui_count):
        KumiteScoringService.apply_penalty(
            match_id=sample_match.id,
            participant=Participant.AKA,
            penalty_type=PenaltyType.CHUI,
            reason=f"CHUI #{i + 1}",
            applied_by_id=sample_user.id,
        )

    state = KumiteMatchState()
    with rx.session() as session:
        state._sync_from_match(session=session, match_id=sample_match.id)

    assert state.aka_penalty_slots == expected_slots


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_exhibition_mode_penalty_is_noop_with_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No active match must not hit service and must warn operator."""
    state = KumiteMatchState()
    state.match_id = 0

    mock_apply_penalty = Mock()
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.kumite_scoring_service.apply_penalty",
        mock_apply_penalty,
    )
    toast_warning = Mock(return_value="toast-no-match")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.warning", toast_warning
    )

    events = [
        event async for event in state.apply_penalty_cumulative(participant="AKA")
    ]

    assert events == ["toast-no-match"]
    toast_warning.assert_called_once_with("No active match")
    mock_apply_penalty.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_undo_last_action_syncs_state_after_service_undo(
    sample_match,
    sample_user,
) -> None:
    """Undo event consumes service path and refreshes synced vars."""
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        session.add(match)
        session.commit()

    state = KumiteMatchState()
    with rx.session() as session:
        state._sync_from_match(session=session, match_id=sample_match.id)

    events = [
        event
        async for event in state.apply_score(
            participant=Participant.AKA.value,
            score_type=ScoreType.YUKO.value,
            applied_by_id=sample_user.id,
        )
    ]
    assert events == []
    assert state.aka_score == 1

    undo_events = [event async for event in state.undo_last_action()]
    assert undo_events == []
    assert state.aka_score == 0

    with rx.session() as session:
        logs = session.exec(
            select(MatchActionLog).where(MatchActionLog.match_id == sample_match.id)
        ).all()
        assert logs == []


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_undo_last_action_blocks_shikkaku_path(
    sample_match,
    sample_user,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scoreboard undo must explicitly reject SHIKKAKU actions."""
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        session.add(match)
        session.commit()

    KumiteScoringService.apply_penalty(
        match_id=sample_match.id,
        participant=Participant.AKA,
        penalty_type=PenaltyType.SHIKKAKU,
        reason="DQ",
        applied_by_id=sample_user.id,
    )

    state = KumiteMatchState()
    with rx.session() as session:
        state._sync_from_match(session=session, match_id=sample_match.id)

    toast_error = Mock(return_value="toast-shikkaku")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.error", toast_error
    )

    events = [event async for event in state.undo_last_action()]

    assert events == ["toast-shikkaku"]
    toast_error.assert_called_once()
    with rx.session() as session:
        penalties = session.exec(
            select(Penalty).where(Penalty.match_id == sample_match.id)
        ).all()
    assert any(p.penalty_type == PenaltyType.SHIKKAKU.value for p in penalties)
