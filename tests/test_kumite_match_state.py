"""Tests for KumiteMatchState penalty/timer synchronization."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest
import reflex as rx
from reflex.istate.data import PageData
from sqlmodel import select

from kakumi_app.models.tournament_model import (
    Match,
    MatchActionLog,
    MatchStatus,
    Participant,
    Penalty,
    PenaltyType,
    ScoreType,
    TournamentCategory,
)
from kakumi_app.services.kumite_scoring_service import KumiteScoringService
from kakumi_app.services.exceptions import (
    AthleteSchedulingConflictError,
    PenaltyRemovalNotAllowedError,
)
from kakumi_app.states.kumite_match_state import KumiteMatchState


def _event_fn(event_callback: Any) -> Any:
    return event_callback.fn


def _set_match_route_param(state: KumiteMatchState, match_id: int | str) -> None:
    """Inject route params into state router for tests."""
    object.__setattr__(
        state.router,
        "_page",
        PageData(params={"match_id": str(match_id)}),
    )


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
async def test_enable_exhibition_mode_publishes_exhibition_secondary_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KumiteMatchState()

    calls: dict[str, object] = {}

    class _FakeDisplaySession:
        display_key = "kumite-exh-key"

    def _ensure(**kwargs):
        calls["ensure"] = kwargs
        return _FakeDisplaySession()

    def _publish(*, display_key: str, snapshot: dict[str, object]):
        calls["publish"] = {
            "display_key": display_key,
            "snapshot": snapshot,
        }
        return _FakeDisplaySession()

    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.SecondaryDisplayService.ensure_display_session",
        _ensure,
    )
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.SecondaryDisplayService.publish_snapshot",
        _publish,
    )

    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)

    assert calls["ensure"] == {
        "modality": "KUMITE",
        "source_kind": "EXHIBITION",
        "match_id": None,
    }
    assert state.public_display_key == "kumite-exh-key"
    snapshot = calls["publish"]["snapshot"]  # type: ignore[index]
    assert snapshot["source_kind"] == "EXHIBITION"
    assert snapshot["match_id"] is None


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
    assert state.aka_senshu is False
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
async def test_exhibition_mode_penalty_mutates_local_slots_without_db_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)

    mock_apply_penalty = Mock()
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.kumite_scoring_service.apply_penalty",
        mock_apply_penalty,
    )

    events = [
        event
        async for event in state.apply_penalty_cumulative(participant="AKA")
    ]

    assert events == []
    assert state.aka_penalty_slots["C1"] is True
    assert state.aka_penalty_slots["C2"] is False
    mock_apply_penalty.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_exhibition_mode_hansoku_emits_winner_toast_and_ends_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)
    state.timer_running = True
    state.aka_penalty_slots = {
        "C1": True,
        "C2": True,
        "C3": True,
        "HC": True,
        "H": False,
    }

    toast_success = Mock(return_value="toast-exh-hansoku")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.success",
        toast_success,
    )

    events = [event async for event in state.apply_penalty_cumulative("AKA")]

    assert events == ["toast-exh-hansoku"]
    assert state.aka_penalty_slots["H"] is True
    assert state.timer_running is False
    assert state.match_end_modal_open is False
    assert state.hantei_required is False
    assert state.match_end_reason == "HANSOKU"
    assert state.match_winner_participant == "AO"
    toast_success.assert_called_once_with("¡Combate terminado!\nGanador: AO")


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


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_load_match_from_route_initializes_real_match_timer_and_identity(
    sample_match,
) -> None:
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        session.add(match)
        session.commit()

    state = KumiteMatchState()
    _set_match_route_param(state, sample_match.id)

    await _event_fn(KumiteMatchState.load_match)(state)

    assert state.match_id == sample_match.id
    assert state.has_active_match is True
    assert state.is_exhibition_mode is False
    assert state.timer_seconds == 180
    assert state.timer_formatted == "03:00"
    assert state.timer_running is False


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_load_match_from_route_uses_category_duration_seconds(
    sample_match,
) -> None:
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        category = session.get(TournamentCategory, match.category_id)
        assert category is not None
        category.match_duration_seconds = 120
        session.add(category)
        session.commit()

    state = KumiteMatchState()
    _set_match_route_param(state, sample_match.id)

    await _event_fn(KumiteMatchState.load_match)(state)

    assert state.timer_seconds == 120
    assert state.timer_formatted == "02:00"


@pytest.mark.asyncio
@pytest.mark.anyio
@pytest.mark.parametrize("params", [{}, {"match_id": ""}, {"match_id": "oops"}])
async def test_load_match_invalid_or_missing_route_stays_real_route_safe_state(
    params: dict[str, str],
) -> None:
    state = KumiteMatchState()
    object.__setattr__(state.router, "_page", PageData(params=params))

    await _event_fn(KumiteMatchState.load_match)(state)

    assert state.match_id == 0
    assert state.has_active_match is False
    assert state.is_exhibition_mode is False
    assert state.error_message == "ID de encuentro inválido"
    assert state.timer_running is False


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_load_match_not_found_stays_real_route_safe_state() -> None:
    state = KumiteMatchState()
    _set_match_route_param(state, 999999)

    await _event_fn(KumiteMatchState.load_match)(state)

    assert state.match_id == 0
    assert state.has_active_match is False
    assert state.is_exhibition_mode is False
    assert state.error_message == "Encuentro no encontrado"
    assert state.timer_running is False


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_timer_start_tick_stop_reset_end_flow_for_real_match(
    sample_match,
) -> None:
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        session.add(match)
        session.commit()

    state = KumiteMatchState()
    _set_match_route_param(state, sample_match.id)
    await _event_fn(KumiteMatchState.load_match)(state)

    state.timer_seconds = 2
    events = [event async for event in state.start_timer()]
    assert len(events) == 1
    assert state.timer_running is True

    first_tick_events = [event async for event in state.tick_timer()]
    assert first_tick_events == []
    assert state.timer_seconds == 1
    assert state.timer_running is True

    await _event_fn(KumiteMatchState.stop_timer)(state)
    assert state.timer_running is False

    reset_events = [event async for event in state.reset_timer()]
    assert reset_events == []
    assert state.timer_seconds == 180
    assert state.timer_formatted == "03:00"

    state.timer_seconds = 1
    restart_events = [event async for event in state.start_timer()]
    assert len(restart_events) == 1
    end_events = [event async for event in state.tick_timer()]
    assert end_events == []
    assert state.timer_seconds == 0
    assert state.timer_running is False
    assert state.match_end_modal_open is True
    assert state.match_end_reason == "HANTEI_REQUIRED"


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_exhibition_mode_can_start_timer_without_active_match() -> None:
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)

    events = [event async for event in state.start_timer()]

    assert len(events) == 1
    assert state.is_exhibition_mode is True
    assert state.has_active_match is False
    assert state.timer_running is True


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_run_timer_loop_decrements_and_stops_with_toast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)
    state.timer_seconds = 1
    state.timer_running = True
    state._timer_loop_active = True

    async def _fast_sleep(_: float) -> None:
        return None

    toast_success = Mock(return_value="toast-end")
    monkeypatch.setattr("asyncio.sleep", _fast_sleep)
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.success",
        toast_success,
    )

    events = [event async for event in _event_fn(KumiteMatchState.run_timer_loop)(state)]

    assert events == []
    assert state.timer_seconds == 0
    assert state.timer_running is False
    assert state._timer_loop_active is False
    assert state.match_end_modal_open is True
    assert state.match_end_reason == "HANTEI_REQUIRED"
    toast_success.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_real_match_guard_blocks_timer_reset_without_active_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KumiteMatchState()
    state.match_id = 0
    state.timer_seconds = 47

    toast_warning = Mock(return_value="toast-no-match")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.warning", toast_warning
    )

    events = [event async for event in state.reset_timer()]

    assert events == ["toast-no-match"]
    assert state.timer_seconds == 47


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_exhibition_mode_reset_timer_uses_exhibition_base_without_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)
    state.timer_base_seconds = 75
    state.timer_seconds = 12

    toast_warning = Mock(return_value="toast-no-match")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.warning", toast_warning
    )

    events = [event async for event in state.reset_timer()]

    assert events == []
    assert state.timer_seconds == 75
    toast_warning.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_set_timer_updates_timer_base_and_seconds_in_exhibition_mode() -> None:
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)
    state.timer_seconds = 12

    events = [event async for event in state.set_timer(60)]

    assert events == []
    assert state.timer_base_seconds == 60
    assert state.timer_seconds == 60
    assert state.timer_running is False


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_add_or_substract_timer_changes_seconds_with_floor_zero() -> None:
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)
    state.timer_seconds = 5

    plus_events = [event async for event in state.add_or_substract_timer(10)]
    assert plus_events == []
    assert state.timer_seconds == 15

    minus_events = [event async for event in state.add_or_substract_timer(-20)]
    assert minus_events == []
    assert state.timer_seconds == 0


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_apply_score_in_exhibition_mode_does_not_auto_assign_senshu() -> None:
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)

    events = [
        event
        async for event in state.apply_score(
            participant=Participant.AKA.value,
            score_type=ScoreType.YUKO.value,
        )
    ]

    assert events == []
    assert state.aka_score == 1
    assert state.ao_score == 0
    assert state.aka_senshu is False
    assert state.ao_senshu is False


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_manual_senshu_apply_and_revoke_exhibition_mode() -> None:
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)

    apply_events = [
        event
        async for event in state.apply_manual_senshu(participant=Participant.AKA.value)
    ]
    assert apply_events == []
    assert state.aka_senshu is True
    assert state.ao_senshu is False

    revoke_events = [
        event
        async for event in state.revoke_manual_senshu(participant=Participant.AKA.value)
    ]
    assert revoke_events == []
    assert state.aka_senshu is False


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_exhibition_undo_restores_manual_senshu_snapshot() -> None:
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)

    apply_events = [
        event
        async for event in state.apply_manual_senshu(participant=Participant.AKA.value)
    ]
    assert apply_events == []
    assert state.aka_senshu is True

    undo_events = [event async for event in state.undo_last_action()]
    assert undo_events == []
    assert state.aka_senshu is False
    assert state.ao_senshu is False


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_manual_senshu_apply_real_mode_calls_service_and_syncs(
    sample_match,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        session.add(match)
        session.commit()

    state = KumiteMatchState()
    _set_match_route_param(state, sample_match.id)
    await _event_fn(KumiteMatchState.load_match)(state)

    def _apply(match_id: int, participant: str):
        assert match_id == sample_match.id
        assert participant == Participant.AKA.value
        with rx.session() as session:
            match_row = session.get(Match, match_id)
            assert match_row is not None
            match_row.aka_senshu = True
            match_row.ao_senshu = False
            session.add(match_row)
            session.commit()
        return SimpleNamespace(success=True, message="SENSHU otorgado")

    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.KumiteScoringService.apply_manual_senshu",
        _apply,
    )

    events = [
        event
        async for event in state.apply_manual_senshu(participant=Participant.AKA.value)
    ]

    assert events == []
    assert state.aka_senshu is True
    assert state.ao_senshu is False


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_manual_senshu_revoke_real_mode_calls_service_and_syncs(
    sample_match,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        match.aka_senshu = True
        session.add(match)
        session.commit()

    state = KumiteMatchState()
    _set_match_route_param(state, sample_match.id)
    await _event_fn(KumiteMatchState.load_match)(state)

    def _revoke(match_id: int, participant: str):
        assert match_id == sample_match.id
        assert participant == Participant.AKA.value
        with rx.session() as session:
            match_row = session.get(Match, match_id)
            assert match_row is not None
            match_row.aka_senshu = False
            session.add(match_row)
            session.commit()
        return SimpleNamespace(success=True, message="SENSHU revocado")

    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.KumiteScoringService.revoke_senshu",
        _revoke,
    )

    events = [
        event
        async for event in state.revoke_manual_senshu(participant=Participant.AKA.value)
    ]

    assert events == []
    assert state.aka_senshu is False


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_manual_senshu_real_mode_service_error_yields_toast(
    sample_match,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        session.add(match)
        session.commit()

    state = KumiteMatchState()
    _set_match_route_param(state, sample_match.id)
    await _event_fn(KumiteMatchState.load_match)(state)

    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.KumiteScoringService.apply_manual_senshu",
        lambda match_id, participant: SimpleNamespace(
            success=False,
            message="No permitido",
        ),
    )
    toast_error = Mock(return_value="toast-senshu-error")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.error",
        toast_error,
    )

    events = [
        event
        async for event in state.apply_manual_senshu(participant=Participant.AKA.value)
    ]

    assert events == ["toast-senshu-error"]
    assert state.error_message == "No permitido"
    toast_error.assert_called_once_with("No permitido")


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_timer_loop_time_expired_points_emits_winner_toast_no_modal(
    sample_match,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Timer en cero con ganador automático emite toast y no abre modal."""
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        match.aka_score = 3
        match.ao_score = 1
        session.add(match)
        session.commit()

    state = KumiteMatchState()
    _set_match_route_param(state, sample_match.id)
    await _event_fn(KumiteMatchState.load_match)(state)
    state.timer_seconds = 1
    state.timer_running = True
    state._timer_loop_active = True

    async def _fast_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("asyncio.sleep", _fast_sleep)

    toast_success = Mock(return_value="toast-finished")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.success",
        toast_success,
    )

    events = [event async for event in _event_fn(KumiteMatchState.run_timer_loop)(state)]

    assert events == ["toast-finished"]
    assert state.timer_running is False
    assert state.match_end_modal_open is False
    assert state.match_end_reason == "TIME_OVER_POINTS"
    assert state.hantei_required is False
    toast_success.assert_called_once_with("¡Combate terminado!\nGanador: AKA")


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_timer_loop_time_expired_hantei_required_blocks_scoring(
    sample_match,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empate sin SENSHU en tiempo exige HANTEI y bloquea score."""
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        match.aka_score = 2
        match.ao_score = 2
        match.aka_senshu = False
        match.ao_senshu = False
        session.add(match)
        session.commit()

    state = KumiteMatchState()
    _set_match_route_param(state, sample_match.id)
    await _event_fn(KumiteMatchState.load_match)(state)
    state.timer_seconds = 1
    state.timer_running = True
    state._timer_loop_active = True

    async def _fast_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("asyncio.sleep", _fast_sleep)

    _ = [event async for event in _event_fn(KumiteMatchState.run_timer_loop)(state)]

    assert state.hantei_required is True
    assert state.match_end_reason == "HANTEI_REQUIRED"

    toast_error = Mock(return_value="toast-hantei-block")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.error",
        toast_error,
    )

    score_events = [
        event
        async for event in state.apply_score(
            participant=Participant.AKA.value,
            score_type=ScoreType.YUKO.value,
        )
    ]

    assert score_events == ["toast-hantei-block"]
    toast_error.assert_called_once_with("Resolver HANTEI antes de puntuar")


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_apply_hantei_decision_updates_state_and_unblocks_scoring(
    sample_match,
    sample_user,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Decisión HANTEI cierra modal y combate queda definitivamente cerrado."""
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        match.aka_score = 1
        match.ao_score = 1
        session.add(match)
        session.commit()

    state = KumiteMatchState()
    _set_match_route_param(state, sample_match.id)
    await _event_fn(KumiteMatchState.load_match)(state)
    state.hantei_required = True
    state.match_end_modal_open = True
    state.match_end_reason = "HANTEI_REQUIRED"

    toast_success = Mock(return_value="toast-finished")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.success",
        toast_success,
    )

    events = [
        event
        async for event in state.apply_hantei_decision(
            winner_participant=Participant.AKA.value,
        )
    ]
    assert events == ["toast-finished"]
    assert state.hantei_required is False
    assert state.match_end_modal_open is False
    assert state.match_end_reason == "HANTEI_DECISION"
    toast_success.assert_called_once_with("¡Combate terminado!\nGanador: AKA")

    toast_error = Mock(return_value="toast-completed")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.error",
        toast_error,
    )

    score_events = [
        event
        async for event in state.apply_score(
            participant=Participant.AKA.value,
            score_type=ScoreType.YUKO.value,
            applied_by_id=sample_user.id,
        )
    ]

    assert score_events == ["toast-completed"]
    toast_error.assert_called_once_with("Match no está en progreso")


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_apply_score_superiority_emits_winner_toast_and_stops_timer(
    sample_match,
    sample_user,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Superiority por score en apply_score emite toast y no modal."""
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        match.aka_score = 6
        match.ao_score = 0
        session.add(match)
        session.commit()

    state = KumiteMatchState()
    _set_match_route_param(state, sample_match.id)
    await _event_fn(KumiteMatchState.load_match)(state)
    state.timer_running = True

    toast_success = Mock(return_value="toast-finished")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.success",
        toast_success,
    )

    events = [
        event
        async for event in state.apply_score(
            participant=Participant.AKA.value,
            score_type=ScoreType.WAZA_ARI.value,
            applied_by_id=sample_user.id,
        )
    ]

    assert events == ["toast-finished"]
    assert state.match_end_modal_open is False
    assert state.match_end_reason == "SUPERIORITY"
    assert state.timer_running is False
    toast_success.assert_called_once_with("¡Combate terminado!\nGanador: AKA")


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_tick_timer_real_match_end_emits_winner_toast_no_modal(
    sample_match,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cuando vence tiempo real automático emite toast exacto y no modal."""
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        match.aka_score = 2
        match.ao_score = 0
        session.add(match)
        session.commit()

    state = KumiteMatchState()
    _set_match_route_param(state, sample_match.id)
    await _event_fn(KumiteMatchState.load_match)(state)
    state.timer_seconds = 1
    state.timer_running = True

    toast_success = Mock(return_value="toast-end")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.success",
        toast_success,
    )

    events = [event async for event in state.tick_timer()]

    assert events == ["toast-end"]
    assert state.timer_seconds == 0
    assert state.timer_running is False
    assert state.match_end_modal_open is False
    assert state.match_end_reason == "TIME_OVER_POINTS"
    assert state.aka_score_color == "gold"
    assert state.ao_score_color == "gray"
    toast_success.assert_called_once_with("¡Combate terminado!\nGanador: AKA")


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_tick_timer_real_match_time_over_senshu_emits_toast_no_modal(
    sample_match,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Time-over por SENSHU no abre dialog; emite toast exacto."""
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        match.aka_score = 2
        match.ao_score = 2
        match.aka_senshu = True
        match.ao_senshu = False
        session.add(match)
        session.commit()

    state = KumiteMatchState()
    _set_match_route_param(state, sample_match.id)
    await _event_fn(KumiteMatchState.load_match)(state)
    state.timer_seconds = 1
    state.timer_running = True

    toast_success = Mock(return_value="toast-end")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.success",
        toast_success,
    )

    events = [event async for event in state.tick_timer()]

    assert events == ["toast-end"]
    assert state.timer_seconds == 0
    assert state.timer_running is False
    assert state.match_end_modal_open is False
    assert state.match_end_reason == "TIME_OVER_SENSHU"
    assert state.aka_score_color == "gold"
    assert state.ao_score_color == "gray"
    toast_success.assert_called_once_with("¡Combate terminado!\nGanador: AKA")


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_tick_timer_real_match_time_over_senshu_ao_winner_sets_score_colors(
    sample_match,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AO winner at timeout renders AO gold and AKA gray contract."""
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        match.aka_score = 1
        match.ao_score = 1
        match.aka_senshu = False
        match.ao_senshu = True
        session.add(match)
        session.commit()

    state = KumiteMatchState()
    _set_match_route_param(state, sample_match.id)
    await _event_fn(KumiteMatchState.load_match)(state)
    state.timer_seconds = 1
    state.timer_running = True

    toast_success = Mock(return_value="toast-end")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.success",
        toast_success,
    )

    events = [event async for event in state.tick_timer()]

    assert events == ["toast-end"]
    assert state.timer_seconds == 0
    assert state.timer_running is False
    assert state.match_end_modal_open is False
    assert state.match_end_reason == "TIME_OVER_SENSHU"
    assert state.aka_score_color == "gray"
    assert state.ao_score_color == "gold"
    toast_success.assert_called_once_with("¡Combate terminado!\nGanador: AO")


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_tick_timer_exhibition_time_over_points_emits_winner_toast_no_modal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exhibition timeout by points emite toast exacto y no modal."""
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)
    state.aka_score = 3
    state.ao_score = 1
    state.timer_seconds = 1
    state.timer_running = True

    toast_success = Mock(return_value="toast-end")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.success",
        toast_success,
    )

    events = [event async for event in state.tick_timer()]

    assert events == ["toast-end"]
    assert state.timer_seconds == 0
    assert state.timer_running is False
    assert state.match_end_modal_open is False
    assert state.match_end_reason == "TIME_OVER_POINTS"
    assert state.hantei_required is False
    toast_success.assert_called_once_with("¡Combate terminado!\nGanador: AKA")


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_tick_timer_exhibition_time_over_senshu_emits_toast_no_modal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exhibition time-over por SENSHU no abre dialog; emite toast exacto."""
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)
    state.aka_score = 1
    state.ao_score = 1
    state.aka_senshu = False
    state.ao_senshu = True
    state.timer_seconds = 1
    state.timer_running = True

    toast_success = Mock(return_value="toast-end")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.success",
        toast_success,
    )

    events = [event async for event in state.tick_timer()]

    assert events == ["toast-end"]
    assert state.timer_seconds == 0
    assert state.timer_running is False
    assert state.match_end_modal_open is False
    assert state.match_end_reason == "TIME_OVER_SENSHU"
    assert state.hantei_required is False
    toast_success.assert_called_once_with("¡Combate terminado!\nGanador: AO")


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_tick_timer_exhibition_draw_requires_hantei_and_allows_decision() -> None:
    """Exhibition tie timeout requires HANTEI and operator can resolve winner."""
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)
    state.aka_score = 2
    state.ao_score = 2
    state.timer_seconds = 1
    state.timer_running = True

    timer_events = [event async for event in state.tick_timer()]

    assert timer_events == []
    assert state.match_end_modal_open is True
    assert state.match_end_reason == "HANTEI_REQUIRED"
    assert state.hantei_required is True

    toast_success = Mock(return_value="toast-finished")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.success",
        toast_success,
    )

    decision_events = [
        event
        async for event in state.apply_hantei_decision(
            winner_participant=Participant.AO.value,
        )
    ]

    assert decision_events == ["toast-finished"]
    assert state.match_end_reason == "HANTEI_DECISION"
    assert state.match_end_modal_open is False
    assert state.hantei_required is False
    toast_success.assert_called_once_with("¡Combate terminado!\nGanador: AO")
    monkeypatch.undo()


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_apply_score_exhibition_superiority_emits_winner_toast_and_stops_timer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exhibition superiority emite toast exacto y no abre modal."""
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)
    state.aka_score = 6
    state.ao_score = 0
    state.timer_running = True

    toast_success = Mock(return_value="toast-finished")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.success",
        toast_success,
    )

    events = [
        event
        async for event in state.apply_score(
            participant=Participant.AKA.value,
            score_type=ScoreType.WAZA_ARI.value,
        )
    ]

    assert events == ["toast-finished"]
    assert state.aka_score == 8
    assert state.match_end_modal_open is False
    assert state.match_end_reason == "SUPERIORITY"
    assert state.timer_running is False
    toast_success.assert_called_once_with("¡Combate terminado!\nGanador: AKA")


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_reset_points_exhibition_mode_clears_score_senshu_and_penalties() -> None:
    """Reset puntos en exhibition limpia score/senshu/penalidades."""
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)
    state.aka_score = 4
    state.ao_score = 2
    state.aka_senshu = True
    state.ao_senshu = False
    state.aka_penalty_slots = {
        "C1": True,
        "C2": True,
        "C3": False,
        "HC": False,
        "H": False,
    }
    state.ao_penalty_slots = {
        "C1": True,
        "C2": False,
        "C3": False,
        "HC": False,
        "H": False,
    }

    await _event_fn(KumiteMatchState.reset_points)(state)

    assert state.aka_score == 0
    assert state.ao_score == 0
    assert state.aka_senshu is False
    assert state.ao_senshu is False
    assert state.aka_penalty_slots == {
        "C1": False,
        "C2": False,
        "C3": False,
        "HC": False,
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
async def test_open_disqualification_dialog_sets_target_and_opens() -> None:
    """Abrir descalificación guarda lado objetivo y abre modal."""
    state = KumiteMatchState()

    await _event_fn(KumiteMatchState.open_disqualification_dialog)(
        state,
        participant=Participant.AKA.value,
    )

    assert state.disqualification_dialog_open is True
    assert state.disqualification_target_participant == Participant.AKA.value


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_apply_disqualification_emits_toast_closes_dialog_and_marks_end(
    sample_match,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Aplicar SHIKKAKU/KIKEN termina combate por toast y sin modal final."""
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        session.add(match)
        session.commit()

    state = KumiteMatchState()
    _set_match_route_param(state, sample_match.id)
    await _event_fn(KumiteMatchState.load_match)(state)
    await _event_fn(KumiteMatchState.open_disqualification_dialog)(
        state,
        participant=Participant.AKA.value,
    )

    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.KumiteScoringService.apply_disqualification",
        lambda match_id, penalized_participant, disqualification_type: SimpleNamespace(
            success=True,
            match_ended=True,
            winner=Participant.AO.value,
            end_reason=disqualification_type,
            hantei_required=False,
            message="ok",
        ),
    )
    toast_success = Mock(return_value="toast-dq")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.success",
        toast_success,
    )

    events = [event async for event in state.apply_disqualification("SHIKKAKU")]

    assert events == ["toast-dq"]
    assert state.disqualification_dialog_open is False
    assert state.disqualification_target_participant == ""
    assert state.match_end_modal_open is False
    assert state.match_end_reason == "SHIKKAKU"
    toast_success.assert_called_once_with("¡Combate terminado!\nGanador: AO")


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_apply_penalty_hansoku_emits_winner_toast_no_modal(
    sample_match,
    sample_user,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Al llegar a HANSOKU termina combate automático por toast (sin dialog)."""
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        session.add(match)
        session.commit()

    for _ in range(3):
        KumiteScoringService.apply_penalty(
            match_id=sample_match.id,
            participant=Participant.AKA,
            penalty_type=PenaltyType.CHUI,
            reason="chui",
            applied_by_id=sample_user.id,
        )
    KumiteScoringService.apply_penalty(
        match_id=sample_match.id,
        participant=Participant.AKA,
        penalty_type=PenaltyType.HANSOKU_CHUI,
        reason="hc",
        applied_by_id=sample_user.id,
    )

    state = KumiteMatchState()
    _set_match_route_param(state, sample_match.id)
    await _event_fn(KumiteMatchState.load_match)(state)

    toast_success = Mock(return_value="toast-hansoku")
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.rx.toast.success",
        toast_success,
    )

    events = [event async for event in state.apply_penalty_cumulative("AKA")]

    assert events == ["toast-hansoku"]
    assert state.match_end_modal_open is False
    assert state.match_end_reason == "HANSOKU"
    toast_success.assert_called_once_with("¡Combate terminado!\nGanador: AO")


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_load_match_publishes_secondary_display_snapshot(
    sample_match,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KumiteMatchState()
    _set_match_route_param(state, sample_match.id)

    calls: dict[str, object] = {}

    class _FakeDisplaySession:
        display_key = "kumite-key"

    def _ensure(**kwargs):
        calls["ensure"] = kwargs
        return _FakeDisplaySession()

    def _publish(*, display_key: str, snapshot: dict[str, object]):
        calls["publish"] = {
            "display_key": display_key,
            "snapshot": snapshot,
        }
        return _FakeDisplaySession()

    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.SecondaryDisplayService.ensure_display_session",
        _ensure,
    )
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.SecondaryDisplayService.publish_snapshot",
        _publish,
    )

    await _event_fn(KumiteMatchState.load_match)(state)

    assert state.public_display_key == "kumite-key"
    assert calls["ensure"] == {
        "modality": "KUMITE",
        "source_kind": "TOURNAMENT",
        "match_id": sample_match.id,
    }
    snapshot = calls["publish"]["snapshot"]  # type: ignore[index]
    assert snapshot["modality"] == "KUMITE"
    assert snapshot["source_kind"] == "TOURNAMENT"


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_reset_points_repulishes_secondary_display_snapshot_in_exhibition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)

    calls: list[dict[str, Any]] = []

    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.SecondaryDisplayService.publish_snapshot",
        lambda *, display_key, snapshot: calls.append(
            {"display_key": display_key, "snapshot": snapshot}
        ),
    )

    await _event_fn(KumiteMatchState.reset_points)(state)

    assert calls
    assert state.public_display_key != ""
    assert calls[-1]["display_key"] == state.public_display_key
    snapshot = calls[-1]["snapshot"]
    assert isinstance(snapshot, dict)
    assert snapshot["source_kind"] == "EXHIBITION"


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_load_match_snapshot_includes_senshu_and_penalties_shape(
    sample_match,
    sample_user,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        match.aka_senshu = True
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
        participant=Participant.AO,
        penalty_type=PenaltyType.CHUI,
        reason="foul",
        applied_by_id=sample_user.id,
    )

    state = KumiteMatchState()
    _set_match_route_param(state, sample_match.id)

    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.SecondaryDisplayService.publish_snapshot",
        lambda *, display_key, snapshot: calls.append(snapshot),
    )

    await _event_fn(KumiteMatchState.load_match)(state)

    assert calls
    snapshot = calls[-1]
    assert snapshot["aka"]["senshu"] is True
    assert snapshot["ao"]["senshu"] is False
    assert snapshot["aka"]["penalties"] == {
        "C1": False,
        "C2": False,
        "C3": False,
        "HC": False,
        "H": False,
    }
    assert snapshot["ao"]["penalties"] == {
        "C1": True,
        "C2": False,
        "C3": False,
        "HC": False,
        "H": False,
    }


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_run_timer_loop_publishes_snapshot_on_each_tick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)
    state.timer_seconds = 2
    state.timer_running = True
    state._timer_loop_active = True

    async def _fast_sleep(_: float) -> None:
        return None

    calls: list[dict[str, Any]] = []
    monkeypatch.setattr("asyncio.sleep", _fast_sleep)
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.SecondaryDisplayService.publish_snapshot",
        lambda *, display_key, snapshot: calls.append(snapshot),
    )

    _ = [event async for event in _event_fn(KumiteMatchState.run_timer_loop)(state)]

    assert len(calls) >= 1
    assert calls[0]["timer_seconds"] == 1
    assert calls[0]["timer_running"] is True


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_run_timer_loop_first_tick_avoids_sync_state_mutation_publisher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Background first tick must not use sync publisher mutating self directly."""
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)
    state.timer_seconds = 2
    state.timer_running = True
    state._timer_loop_active = True

    sleep_calls = {"count": 0}

    async def _stop_after_first_tick(_: float) -> None:
        sleep_calls["count"] += 1
        if sleep_calls["count"] >= 2:
            raise asyncio.CancelledError

    monkeypatch.setattr("asyncio.sleep", _stop_after_first_tick)
    monkeypatch.setattr(
        KumiteMatchState,
        "_publish_display_snapshot",
        lambda self: (_ for _ in ()).throw(RuntimeError("ImmutableStateError")),
    )
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.SecondaryDisplayService.publish_snapshot",
        lambda *, display_key, snapshot: object(),
    )

    with pytest.raises(asyncio.CancelledError):
        _ = [event async for event in _event_fn(KumiteMatchState.run_timer_loop)(state)]

    assert state.timer_seconds == 1
    assert state.timer_running is True


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_run_timer_loop_stops_without_publish_for_disconnected_viewer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)
    state.timer_seconds = 9
    state.timer_running = True
    state._timer_loop_active = True

    monkeypatch.setattr(
        KumiteMatchState,
        "_is_viewer_connected",
        lambda self: False,
    )

    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.SecondaryDisplayService.publish_snapshot",
        lambda *, display_key, snapshot: calls.append(snapshot),
    )

    _ = [event async for event in _event_fn(KumiteMatchState.run_timer_loop)(state)]

    assert calls == []
    assert state.timer_running is False
    assert state._timer_loop_active is False


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_run_timer_loop_checks_connection_inside_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KumiteMatchState()
    await _event_fn(KumiteMatchState.enable_exhibition_mode)(state)
    state.timer_seconds = 9
    state.timer_running = True
    state._timer_loop_active = True
    baseline_display_status = state.display_status

    connection_sequence = iter([True, False])
    monkeypatch.setattr(
        KumiteMatchState,
        "_is_viewer_connected",
        lambda self: next(connection_sequence),
    )

    async def _fast_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("asyncio.sleep", _fast_sleep)

    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.SecondaryDisplayService.publish_snapshot",
        lambda *, display_key, snapshot: calls.append(snapshot),
    )

    _ = [event async for event in _event_fn(KumiteMatchState.run_timer_loop)(state)]

    assert calls == []
    assert state.timer_seconds == 9
    assert state.timer_running is False
    assert state._timer_loop_active is False
    assert state.last_action_label == ""
    assert state.display_status == baseline_display_status


def test_publish_display_snapshot_skipped_when_viewer_disconnected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KumiteMatchState()
    state.public_display_key = "kumite-key"
    object.__setattr__(
        state.router,
        "session",
        type("Session", (), {"client_token": "disconnected-token"})(),
    )

    fake_app = type(
        "App",
        (),
        {
            "_token_manager": type(
                "TokenManager",
                (),
                {"token_to_socket": {}},
            )()
        },
    )()
    monkeypatch.setattr(rx.State, "_get_app", lambda: fake_app, raising=False)

    ensure_calls: list[dict[str, Any]] = []
    publish_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.SecondaryDisplayService.ensure_display_session",
        lambda **kwargs: ensure_calls.append(kwargs),
    )
    monkeypatch.setattr(
        "kakumi_app.states.kumite_match_state.SecondaryDisplayService.publish_snapshot",
        lambda **kwargs: publish_calls.append(kwargs),
    )

    state._publish_display_snapshot()

    assert ensure_calls == []
    assert publish_calls == []
    assert state.public_display_key == "kumite-key"
    assert state.display_status == ""
