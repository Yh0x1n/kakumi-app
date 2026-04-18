"""Tests for KumiteMatchState penalty/timer synchronization."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from kakumi_app.models.tournament_model import PenaltyType
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
