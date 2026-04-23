"""Batch 1 quick-wins/async/rbac behavioral regression tests (strict TDD)."""

from __future__ import annotations

import importlib
import inspect
import sys
from datetime import datetime

import pytest
import reflex as rx
from reflex.event import EventHandler

from kakumi_app.services.auth_service import AuthService
from kakumi_app.states.athlete_state import AthleteState
from kakumi_app.states.auth_state import AuthState
from kakumi_app.states.referee_state import RefereeState
from kakumi_app.states.team_state import TeamState
from kakumi_app.states.tournament_state import TournamentState
from kakumi_app.states.viewer_state import ViewerState


def _event_fn(cls: type, method_name: str):
    handler = getattr(cls, method_name)
    assert isinstance(handler, EventHandler)
    assert callable(handler.fn)
    return handler.fn


def test_a_tokens_are_hex_strings() -> None:
    from kakumi_app.styles import tokens

    names = [
        "BRAND_RED",
        "BRAND_RED_HOVER",
        "TEXT_WHITE",
        "ACCENT_GOLD",
        "HOVER_GRAY",
        "BORDER_SUBTLE",
    ]
    for name in names:
        value = getattr(tokens, name)
        assert isinstance(value, str)
        assert value
        assert value.startswith("#")


def test_a_auth_last_activity_is_iso_string() -> None:
    state = AuthState()
    assert isinstance(state.last_activity, str)
    datetime.fromisoformat(state.last_activity)
    state.update_last_activity()
    datetime.fromisoformat(state.last_activity)


def test_a_viewer_filtered_categories_behaves_as_computed_var() -> None:
    descriptor = ViewerState.__dict__.get("filtered_categories")
    assert descriptor is not None
    assert hasattr(descriptor, "__get__")

    state = ViewerState()
    state.categories = [{"id": 1, "name": "Kata", "type": "kata"}]
    assert state.filtered_categories == state.categories


def test_b1_required_handlers_are_reflex_event_handlers() -> None:
    required = [
        (AthleteState, "load_athletes"),
        (AuthState, "login"),
        (RefereeState, "load_referees"),
        (TournamentState, "open_registrations"),
        (ViewerState, "load_tournament_by_id"),
    ]
    for cls, method_name in required:
        _event_fn(cls, method_name)


def test_b2_db_handlers_are_async_event_functions() -> None:
    expected_async = [
        (AthleteState, "load_athletes"),
        (AthleteState, "save_athlete"),
        (AthleteState, "delete_athlete"),
        (AuthState, "login"),
        (RefereeState, "load_referees"),
        (TeamState, "load_teams"),
    ]
    for cls, method_name in expected_async:
        fn = _event_fn(cls, method_name)
        assert inspect.iscoroutinefunction(fn)


def test_b2_filter_handlers_are_async_to_avoid_sync_async_mixing() -> None:
    for cls, method_name in [
        (AthleteState, "filter_athletes"),
        (RefereeState, "filter_referees"),
        (TeamState, "filter_teams"),
    ]:
        fn = _event_fn(cls, method_name)
        assert inspect.iscoroutinefunction(fn)


def test_b2_check_session_timeout_is_async_to_await_logout() -> None:
    fn = _event_fn(AuthState, "check_session_timeout")
    assert inspect.iscoroutinefunction(fn)


@pytest.mark.anyio
async def test_b2_check_session_timeout_returns_false_for_fresh_session() -> None:
    state = AuthState()
    state.is_authenticated = True
    state.last_activity = datetime.utcnow().isoformat()
    expired = await AuthState.check_session_timeout.fn(state)
    assert expired is False


def test_d_rbac_single_source_contract_and_behavior() -> None:
    assert not hasattr(AuthState, "require_role")
    assert not hasattr(AuthState, "ROLE_HIERARCHY")
    assert not hasattr(TournamentState, "_check_permission")

    assert hasattr(AuthService, "check_permission")
    signature = inspect.signature(AuthService.check_permission)
    assert tuple(signature.parameters.keys()) == ("user_role", "required_role")

    assert AuthService.check_permission("ADMIN", "OPERATOR") is True
    assert AuthService.check_permission("VIEWER", "ADMIN") is False


def test_d_legacy_rbac_role_helpers_are_removed() -> None:
    from kakumi_app.auth import rbac

    assert not hasattr(rbac, "ROLE_HIERARCHY")
    assert not hasattr(rbac, "require_role")


def test_b2_athlete_validate_form_approval_valid_case() -> None:
    state = AthleteState()
    state.name = "Jane Doe"
    state.date_of_birth = "2000-05-01"
    state.gender = "FEMALE"
    state.weight_kg = "55"
    state.belt_rank = "Dan 1"

    assert state.validate_form() is True
    assert state.error_message == ""


def test_b2_athlete_validate_form_approval_invalid_weight_case() -> None:
    state = AthleteState()
    state.name = "Jane Doe"
    state.date_of_birth = "2000-05-01"
    state.gender = "FEMALE"
    state.weight_kg = "39.9"

    assert state.validate_form() is False
    assert state.error_message == "Weight must be between 40.0 and 120.0 kg"


def test_reg_admin_routes_registered_in_reflex_page_registry() -> None:
    import kakumi_app.kakumi_app  # noqa: F401

    page_module = importlib.import_module("reflex.page")
    pages = page_module.DECORATED_PAGES.get("kakumi_app", [])
    routes = {config.get("route") for _, config in pages}

    assert "/admin/athletes" in routes
    assert "/admin/referees" in routes
    assert "/admin/teams" in routes


@pytest.mark.anyio
async def test_login_page_on_load_calls_admin_init_only_when_invoked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    @rx.event
    async def fake_create_initial_admin(self) -> None:
        calls.append("admin")

    @rx.event
    async def fake_check_auth(self) -> None:
        calls.append("check_auth")

    monkeypatch.setattr(AuthState, "create_initial_admin", fake_create_initial_admin)
    monkeypatch.setattr(AuthState, "check_auth", fake_check_auth)

    page_module = importlib.import_module("reflex.page")
    original_count = len(page_module.DECORATED_PAGES.get("kakumi_app", []))

    sys.modules.pop("kakumi_app.pages.auth.login", None)
    importlib.import_module("kakumi_app.pages.auth.login")

    # Import-time behavior: no admin creation side effect.
    assert calls == []

    all_pages = page_module.DECORATED_PAGES.get("kakumi_app", [])
    login_configs = [
        config
        for _, config in all_pages[original_count:]
        if config.get("route") == "/login"
    ]
    assert login_configs
    on_load = login_configs[-1].get("on_load")
    assert isinstance(on_load, list)

    assert fake_create_initial_admin in on_load

    state = AuthState()
    await on_load[0](state)
    assert calls == ["admin"]
