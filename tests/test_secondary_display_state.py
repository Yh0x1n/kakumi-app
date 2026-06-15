"""Behavioral tests for secondary display read-only state and page route.

Keeps all state behavioral tests, computed var accessors, and polling logic.
Removes brittle UI string snapshot assertions.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
import reflex as rx
from reflex.istate.data import PageData

from kakumi_app.states.secondary_display_state import SecondaryDisplayState
from kakumi_app.pages.public_display import public_display_page


def _event_fn(event_callback: Any) -> Any:
    return event_callback.fn


def _set_display_route_param(state: SecondaryDisplayState, display_key: str) -> None:
    object.__setattr__(
        state.router,
        "_page",
        PageData(params={"display_key": display_key}),
    )


def test_public_display_page_returns_component() -> None:
    """public_display_page must return a valid rx.Component."""
    assert isinstance(public_display_page(), rx.Component)


# =============================================================================
# Behavioral tests: load_display
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_load_display_reports_missing_key_error() -> None:
    state = SecondaryDisplayState()
    _set_display_route_param(state, "missing-key")

    await _event_fn(SecondaryDisplayState.load_display)(state)

    assert state.current_display_key == "missing-key"
    assert state.has_snapshot is False
    assert state.error_message == "Pantalla no encontrada"


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_load_display_flags_stale_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SecondaryDisplayState()
    _set_display_route_param(state, "stale-key")

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.SecondaryDisplayService.read_snapshot",
        lambda display_key, stale_after_seconds: SimpleNamespace(
            status="stale",
            snapshot={"modality": "KATA", "title": "Kata"},
            updated_at=None,
        ),
    )

    await _event_fn(SecondaryDisplayState.load_display)(state)

    assert state.is_stale is True
    assert state.has_snapshot is True
    assert state.modality == "KATA"


# =============================================================================
# Behavioral tests: refresh_snapshot
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_refresh_snapshot_updates_modality_and_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SecondaryDisplayState()
    state.current_display_key = "ok-key"

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.SecondaryDisplayService.read_snapshot",
        lambda display_key, stale_after_seconds: SimpleNamespace(
            status="ok",
            snapshot={
                "modality": "KUMITE",
                "title": "Combate en vivo",
                "aka": {"name": "AKA", "score": 2},
                "ao": {"name": "AO", "score": 1},
            },
            updated_at=None,
        ),
    )

    await _event_fn(SecondaryDisplayState.refresh_snapshot)(state)

    assert state.error_message == ""
    assert state.has_snapshot is True
    assert state.modality == "KUMITE"
    assert state.snapshot["title"] == "Combate en vivo"


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_refresh_snapshot_exposes_kumite_senshu_and_penalties(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SecondaryDisplayState()
    state.current_display_key = "kumite-live"

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.SecondaryDisplayService.read_snapshot",
        lambda display_key, stale_after_seconds: SimpleNamespace(
            status="ok",
            snapshot={
                "modality": "KUMITE",
                "aka": {
                    "name": "AKA",
                    "score": 3,
                    "senshu": True,
                    "penalties": {
                        "C1": True,
                        "C2": False,
                        "C3": True,
                        "HC": False,
                        "H": False,
                    },
                },
                "ao": {
                    "name": "AO",
                    "score": 1,
                    "senshu": False,
                    "penalties": {
                        "C1": False,
                        "C2": False,
                        "C3": False,
                        "HC": False,
                        "H": False,
                    },
                },
            },
            updated_at=None,
        ),
    )

    await _event_fn(SecondaryDisplayState.refresh_snapshot)(state)

    assert state.kumite_aka_senshu is True
    assert state.kumite_ao_senshu is False
    assert state.kumite_aka_penalties_label == "C1, C3"
    assert state.kumite_ao_penalties_label == "Ninguna"


# =============================================================================
# Computed var accessors
# =============================================================================


def test_kata_informal_accessors_project_single_athlete_and_results() -> None:
    state = SecondaryDisplayState()
    state.snapshot = {
        "kata_mode": "INFORMAL",
        "informal": {
            "athlete_name": "Lucía",
            "results": ["1. Lucía — 8.200", "2. Sofia — 8.100"],
        },
    }

    assert state.kata_is_informal_mode is True
    assert state.kata_informal_athlete_name == "Lucía"
    assert state.kata_informal_results == ["1. Lucía — 8.200", "2. Sofia — 8.100"]


def test_kata_majority_tally_accessors_project_vote_count_copy() -> None:
    state = SecondaryDisplayState()
    state.snapshot = {
        "majority_tally_visible": True,
        "majority_tally": "AKA 3 - AO 2",
    }

    assert state.kata_majority_tally_visible is True
    assert state.kata_majority_tally == "AKA 3 - AO 2"


def test_kata_majority_tally_accessors_project_vote_counts_for_big_labels() -> None:
    state = SecondaryDisplayState()
    state.snapshot = {
        "majority_tally_visible": True,
        "majority_aka_votes": 2,
        "majority_ao_votes": 3,
        "aka": {"total": "24.100"},
        "ao": {"total": "24.900"},
    }

    assert state.kata_aka_total == "2"
    assert state.kata_ao_total == "3"


# =============================================================================
# Behavioral tests: poll_snapshot_loop
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_poll_snapshot_loop_refreshes_with_state_lock_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SecondaryDisplayState()
    state.current_display_key = "live-key"

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.SecondaryDisplayService.read_snapshot",
        lambda display_key, stale_after_seconds: SimpleNamespace(
            status="ok",
            snapshot={"modality": "KATA", "source_kind": "TOURNAMENT"},
            updated_at=None,
        ),
    )

    async def _cancel_after_first_tick(_: float) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.asyncio.sleep",
        _cancel_after_first_tick,
    )

    with pytest.raises(asyncio.CancelledError):
        await _event_fn(SecondaryDisplayState.poll_snapshot_loop)(state)

    assert state.has_snapshot is True
    assert state.modality == "KATA"
    assert state.error_message == ""


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_poll_snapshot_loop_stops_for_disconnected_viewer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SecondaryDisplayState()
    state.current_display_key = "live-key"

    read_calls = {"count": 0}

    def _read_snapshot(*, display_key: str, stale_after_seconds: int):
        del display_key, stale_after_seconds
        read_calls["count"] += 1
        return SimpleNamespace(status="ok", snapshot={}, updated_at=None)

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.SecondaryDisplayService.read_snapshot",
        _read_snapshot,
    )
    monkeypatch.setattr(
        SecondaryDisplayState,
        "_is_viewer_connected",
        lambda self: False,
    )

    await _event_fn(SecondaryDisplayState.poll_snapshot_loop)(state)

    assert read_calls["count"] == 0


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_viewer_heartbeat_registers_presence_with_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SecondaryDisplayState()
    state.current_display_key = "live-key"
    state._viewer_client_token = "viewer-token"

    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.SecondaryDisplayService.register_viewer_heartbeat",
        lambda *, display_key, client_token: calls.append((display_key, client_token)),
    )

    await _event_fn(SecondaryDisplayState.viewer_heartbeat)(state, "tick")

    assert calls == [("live-key", "viewer-token")]


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_is_viewer_connected_uses_heartbeat_fallback_when_probe_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SecondaryDisplayState()
    state.current_display_key = "live-key"
    state._viewer_client_token = "viewer-token"

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.SecondaryDisplayService.has_recent_viewer_heartbeat",
        lambda *, display_key, client_token, ttl_seconds: (
            display_key == "live-key"
            and client_token == "viewer-token"
            and ttl_seconds >= 1
        ),
    )

    assert state._is_viewer_connected() is True


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_poll_snapshot_loop_stops_after_heartbeat_expiration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SecondaryDisplayState()
    state.current_display_key = "live-key"
    state._viewer_client_token = "viewer-token"

    heartbeat_checks = iter([True, False])
    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.SecondaryDisplayService.has_recent_viewer_heartbeat",
        lambda *, display_key, client_token, ttl_seconds: (
            display_key == "live-key"
            and client_token == "viewer-token"
            and ttl_seconds >= 1
            and next(heartbeat_checks)
        ),
    )

    read_calls = {"count": 0}

    def _read_snapshot(display_key: str, stale_after_seconds: int) -> SimpleNamespace:
        del display_key, stale_after_seconds
        read_calls["count"] += 1
        return SimpleNamespace(
            status="ok", snapshot={"modality": "KATA"}, updated_at=None
        )

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.SecondaryDisplayService.read_snapshot",
        _read_snapshot,
    )

    async def _no_wait(_: float) -> None:
        return None

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.asyncio.sleep",
        _no_wait,
    )

    await _event_fn(SecondaryDisplayState.poll_snapshot_loop)(state)

    assert read_calls["count"] == 1


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_poll_snapshot_loop_applies_idle_backoff_for_unchanged_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SecondaryDisplayState()
    state.current_display_key = "stable-key"

    connectivity_sequence = iter([True, True, True, True, True, True, False])
    monkeypatch.setattr(
        SecondaryDisplayState,
        "_is_viewer_connected",
        lambda self: next(connectivity_sequence),
    )

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.SecondaryDisplayService.read_snapshot",
        lambda display_key, stale_after_seconds: SimpleNamespace(
            status="ok",
            snapshot={"modality": "KATA", "title": "Stable"},
            updated_at=None,
        ),
    )

    sleep_calls: list[float] = []

    async def _record_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.asyncio.sleep",
        _record_sleep,
    )

    await _event_fn(SecondaryDisplayState.poll_snapshot_loop)(state)

    assert sleep_calls == [1.0, 2.0, 4.0]


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_poll_snapshot_loop_applies_error_backoff_after_transient_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SecondaryDisplayState()
    state.current_display_key = "unstable-key"

    connectivity_sequence = iter([True, True, True, True, False])
    monkeypatch.setattr(
        SecondaryDisplayState,
        "_is_viewer_connected",
        lambda self: next(connectivity_sequence),
    )

    read_calls = {"count": 0}

    def _read_snapshot(display_key: str, stale_after_seconds: int) -> SimpleNamespace:
        del display_key, stale_after_seconds
        read_calls["count"] += 1
        if read_calls["count"] == 1:
            raise RuntimeError("temporary DB hiccup")
        return SimpleNamespace(
            status="ok",
            snapshot={"modality": "KUMITE", "title": "Recovered"},
            updated_at=None,
        )

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.SecondaryDisplayService.read_snapshot",
        _read_snapshot,
    )

    sleep_calls: list[float] = []

    async def _record_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.asyncio.sleep",
        _record_sleep,
    )

    await _event_fn(SecondaryDisplayState.poll_snapshot_loop)(state)

    assert sleep_calls == [2.0, 1.0]


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_poll_snapshot_loop_skips_mutation_when_disconnected_during_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SecondaryDisplayState()
    state.current_display_key = "race-key"
    state.snapshot = {"title": "existing"}
    state.has_snapshot = True
    state.error_message = ""

    connectivity_sequence = iter([True, False])
    monkeypatch.setattr(
        SecondaryDisplayState,
        "_is_viewer_connected",
        lambda self: next(connectivity_sequence),
    )

    read_calls = {"count": 0}

    def _read_snapshot(display_key: str, stale_after_seconds: int) -> SimpleNamespace:
        del display_key, stale_after_seconds
        read_calls["count"] += 1
        return SimpleNamespace(
            status="ok",
            snapshot={"modality": "KATA", "title": "new"},
            updated_at=None,
        )

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.SecondaryDisplayService.read_snapshot",
        _read_snapshot,
    )

    sleep_calls: list[float] = []

    async def _record_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.asyncio.sleep",
        _record_sleep,
    )

    await _event_fn(SecondaryDisplayState.poll_snapshot_loop)(state)

    assert read_calls["count"] == 1
    assert sleep_calls == []
    assert state.snapshot == {"title": "existing"}
    assert state.has_snapshot is True
    assert state.modality == ""
    assert state.source_kind == ""
    assert state.error_message == ""


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_reduced_heartbeat_ttl_allows_normal_polling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SecondaryDisplayState()
    state.current_display_key = "ttl-key"
    state._viewer_client_token = "viewer-token"

    monkeypatch.setattr(
        rx.State,
        "_get_app",
        lambda: SimpleNamespace(),
        raising=False,
    )

    ttl_checks: list[int] = []
    heartbeat_sequence = iter([True, True, False])

    def _has_recent_viewer_heartbeat(
        *,
        display_key: str,
        client_token: str,
        ttl_seconds: int,
    ) -> bool:
        assert display_key == "ttl-key"
        assert client_token == "viewer-token"
        ttl_checks.append(ttl_seconds)
        return next(heartbeat_sequence)

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.SecondaryDisplayService.has_recent_viewer_heartbeat",
        _has_recent_viewer_heartbeat,
    )

    read_calls = {"count": 0}

    def _read_snapshot(display_key: str, stale_after_seconds: int) -> SimpleNamespace:
        del display_key, stale_after_seconds
        read_calls["count"] += 1
        return SimpleNamespace(
            status="ok",
            snapshot={"modality": "KUMITE", "title": "Live"},
            updated_at=None,
        )

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.SecondaryDisplayService.read_snapshot",
        _read_snapshot,
    )

    async def _no_wait(_: float) -> None:
        return None

    monkeypatch.setattr(
        "kakumi_app.states.secondary_display_state.asyncio.sleep",
        _no_wait,
    )

    await _event_fn(SecondaryDisplayState.poll_snapshot_loop)(state)

    assert state.viewer_heartbeat_ttl_seconds == 5
    assert read_calls["count"] == 1
    assert state.has_snapshot is True
    assert state.modality == "KUMITE"
    assert ttl_checks == [5, 5, 5]
