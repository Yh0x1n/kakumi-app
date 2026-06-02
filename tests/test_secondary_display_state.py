"""Tests for secondary display read-only state and page route."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
import reflex as rx
from reflex.istate.data import PageData

from kakumi_app.components.public_kata_display import public_kata_display
from kakumi_app.components.public_kumite_display import public_kumite_display
from kakumi_app.pages.public_display import public_display_page
from kakumi_app.states.secondary_display_state import SecondaryDisplayState


def _set_display_route_param(state: SecondaryDisplayState, display_key: str) -> None:
    object.__setattr__(
        state.router,
        "_page",
        PageData(params={"display_key": display_key}),
    )


def _flatten_render_strings(node: object) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        values: list[str] = []
        for value in node.values():
            values.extend(_flatten_render_strings(value))
        return values
    if isinstance(node, list):
        values: list[str] = []
        for item in node:
            values.extend(_flatten_render_strings(item))
        return values
    return []


def _rendered_string(component: rx.Component) -> str:
    return " ".join(
        value.encode("utf-8").decode("unicode_escape")
        for value in _flatten_render_strings(component.render())
    )


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_load_display_reports_missing_key_error() -> None:
    state = SecondaryDisplayState()
    _set_display_route_param(state, "missing-key")

    await SecondaryDisplayState.load_display.fn(state)

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

    await SecondaryDisplayState.load_display.fn(state)

    assert state.is_stale is True
    assert state.has_snapshot is True
    assert state.modality == "KATA"


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

    await SecondaryDisplayState.refresh_snapshot.fn(state)

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

    await SecondaryDisplayState.refresh_snapshot.fn(state)

    assert state.kumite_aka_senshu is True
    assert state.kumite_ao_senshu is False
    assert state.kumite_aka_penalties_label == "C1, C3"
    assert state.kumite_ao_penalties_label == "Ninguna"


def test_public_display_page_contains_read_only_copy() -> None:
    rendered = _rendered_string(public_display_page())

    assert "Pantalla pública" in rendered
    assert "Solo lectura" in rendered
    assert "Actualizar" not in rendered


def test_public_kata_display_uses_fullscreen_viewport_layout_tokens() -> None:
    rendered = _rendered_string(public_kata_display())

    assert "100vw" in rendered
    assert "100vh" in rendered
    assert "45vw" in rendered
    assert "5vw" in rendered
    assert "2vh" in rendered


def test_public_kata_display_includes_judge_detail_copy() -> None:
    rendered = _rendered_string(public_kata_display())

    assert "Detalle jueces" in rendered


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


def test_public_kata_display_does_not_include_centered_tally_copy() -> None:
    rendered = _rendered_string(public_kata_display())

    assert "AKA 3 - AO 2" not in rendered


def test_public_kumite_display_uses_fullscreen_viewport_layout_tokens() -> None:
    rendered = _rendered_string(public_kumite_display())

    assert "100vw" in rendered
    assert "100vh" in rendered
    assert "40vw" in rendered
    assert "20vw" in rendered
    assert "7vw" in rendered
    assert "2vh" in rendered


def test_public_kumite_display_includes_senshu_and_penalty_copy() -> None:
    rendered = _rendered_string(public_kumite_display())

    assert "SENSHU" in rendered
    assert "Penalizaciones" in rendered


def test_public_display_does_not_render_quoted_proxy_expressions() -> None:
    rendered = _rendered_string(public_display_page())

    assert '"(isTrue(' not in rendered


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
        await SecondaryDisplayState.poll_snapshot_loop.fn(state)

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

    await SecondaryDisplayState.poll_snapshot_loop.fn(state)

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

    await SecondaryDisplayState.viewer_heartbeat.fn(state, "tick")

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

    await SecondaryDisplayState.poll_snapshot_loop.fn(state)

    assert read_calls["count"] == 1


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_poll_snapshot_loop_applies_idle_backoff_for_unchanged_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SecondaryDisplayState()
    state.current_display_key = "stable-key"

    connectivity_sequence = iter([True, True, True, False])
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

    await SecondaryDisplayState.poll_snapshot_loop.fn(state)

    assert sleep_calls == [1.0, 2.0, 4.0]


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_poll_snapshot_loop_applies_error_backoff_after_transient_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SecondaryDisplayState()
    state.current_display_key = "unstable-key"

    connectivity_sequence = iter([True, True, False])
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

    await SecondaryDisplayState.poll_snapshot_loop.fn(state)

    assert sleep_calls == [2.0, 1.0]
