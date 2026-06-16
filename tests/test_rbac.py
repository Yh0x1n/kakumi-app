"""Tests for RBAC admin page gates, sidebar role filtering, protected_layout, and integration.

Merged from:
  - test_rbac_admin_gates.py (backbone, trimmed Phase 3)
  - test_rbac_integration.py
"""

from __future__ import annotations

import importlib
import inspect
import sys
from datetime import datetime
from types import SimpleNamespace

import pytest
import reflex as rx
from reflex.event import EventHandler, EventSpec

from kakumi_app.services.auth_service import AuthService
from kakumi_app.states.athlete_state import AthleteState
from kakumi_app.states.auth_state import AuthState, DEV_AUTH_BYPASS
from kakumi_app.states.referee_state import RefereeState
from kakumi_app.states.team_state import TeamState
from kakumi_app.states.tournament_state import TournamentState
from kakumi_app.states.viewer_state import ViewerState


# =============================================================================
# Helper: create an AuthState in a specific role
# =============================================================================


def _state_with_role(role: str, authenticated: bool = True) -> AuthState:
    """Create an AuthState with the given role and authentication status."""
    state = AuthState()
    state.is_authenticated = authenticated
    state.user_role = role
    return state


# =============================================================================
# Parametrized role × permission matrix for _has_permission
# =============================================================================


# (role, authenticated, required_role, expected)
_ACCESS_MATRIX = [
    pytest.param("VIEWER", True, "VIEWER", True, id="viewer_can_access_viewer"),
    pytest.param("VIEWER", True, "OPERATOR", False, id="viewer_denied_operator"),
    pytest.param("VIEWER", True, "ADMIN", False, id="viewer_denied_admin"),
    pytest.param("OPERATOR", True, "VIEWER", True, id="operator_can_access_viewer"),
    pytest.param("OPERATOR", True, "OPERATOR", True, id="operator_can_access_operator"),
    pytest.param("OPERATOR", True, "ADMIN", False, id="operator_denied_admin"),
    pytest.param("ADMIN", True, "VIEWER", True, id="admin_can_access_viewer"),
    pytest.param("ADMIN", True, "OPERATOR", True, id="admin_can_access_operator"),
    pytest.param("ADMIN", True, "ADMIN", True, id="admin_can_access_admin"),
    pytest.param("VIEWER", False, "VIEWER", False, id="unauthenticated_denied_viewer"),
    pytest.param(
        "VIEWER", False, "OPERATOR", False, id="unauthenticated_denied_operator"
    ),
    pytest.param("VIEWER", False, "ADMIN", False, id="unauthenticated_denied_admin"),
]


@pytest.mark.parametrize(
    ("role", "authenticated", "required_role", "expected"),
    _ACCESS_MATRIX,
)
def test_has_permission_matrix(
    role: str,
    authenticated: bool,
    required_role: str,
    expected: bool,
) -> None:
    """Role-based _has_permission must match the access control matrix."""
    state = _state_with_role(role, authenticated)
    assert state._has_permission(required_role) is expected


# =============================================================================
# SCENARIO: DEV_AUTH_BYPASS skips gates
# =============================================================================


def test_dev_bypass_defaults_to_operator() -> None:
    """GIVEN DEV_AUTH_BYPASS is configured
    WHEN _load_user_from_stored runs
    THEN role is OPERATOR and _has_permission("OPERATOR") is True
    """
    state = AuthState()
    state._load_user_from_stored()

    if DEV_AUTH_BYPASS:
        assert state.user_role == "OPERATOR"
        assert state._has_permission("OPERATOR") is True
        assert state._has_permission("ADMIN") is False
        assert state.is_authenticated is True
    else:
        # Not bypassed — no token means unauthenticated
        assert state.is_authenticated is False


# =============================================================================
# Relocated from test_batch1_quick_wins_async_rbac.py
# =============================================================================


def _event_fn(cls: type, method_name: str):
    handler = getattr(cls, method_name)
    assert isinstance(handler, EventHandler)
    assert callable(handler.fn)
    return handler.fn


# Relocated from test_batch1_quick_wins_async_rbac.py — auth state contract
def test_a_auth_last_activity_is_iso_string() -> None:
    state = AuthState()
    assert isinstance(state.last_activity, str)
    datetime.fromisoformat(state.last_activity)
    state.update_last_activity()
    datetime.fromisoformat(state.last_activity)


# Relocated from test_batch1_quick_wins_async_rbac.py — viewer computed var
def test_a_viewer_filtered_categories_behaves_as_computed_var() -> None:
    descriptor = ViewerState.__dict__.get("filtered_categories")
    assert descriptor is not None
    assert hasattr(descriptor, "__get__")

    state = ViewerState()
    state.categories = [{"id": 1, "name": "Kata", "type": "kata"}]
    assert state.filtered_categories == state.categories


# Relocated from test_batch1_quick_wins_async_rbac.py — event handler contract
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


# Relocated from test_batch1_quick_wins_async_rbac.py — async event contract
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


# Relocated from test_batch1_quick_wins_async_rbac.py — async event contract
def test_b2_filter_handlers_are_async_to_avoid_sync_async_mixing() -> None:
    for cls, method_name in [
        (AthleteState, "filter_athletes"),
        (RefereeState, "filter_referees"),
        (TeamState, "filter_teams"),
    ]:
        fn = _event_fn(cls, method_name)
        assert inspect.iscoroutinefunction(fn)


# Relocated from test_batch1_quick_wins_async_rbac.py — async event contract
def test_b2_check_session_timeout_is_async_to_await_logout() -> None:
    fn = _event_fn(AuthState, "check_session_timeout")
    assert inspect.iscoroutinefunction(fn)


@pytest.mark.anyio
async def test_b2_check_session_timeout_returns_none_for_fresh_session() -> None:
    state = AuthState()
    state.is_authenticated = True
    state.last_activity = datetime.utcnow().isoformat()
    result = await AuthState.check_session_timeout.fn(state)
    assert result is None
    assert state.session_expired is False


# Relocated from test_batch1_quick_wins_async_rbac.py — RBAC contract
def test_d_rbac_single_source_contract_and_behavior() -> None:
    assert not hasattr(AuthState, "require_role")
    assert not hasattr(AuthState, "ROLE_HIERARCHY")
    assert not hasattr(TournamentState, "_check_permission")

    assert hasattr(AuthService, "check_permission")
    signature = inspect.signature(AuthService.check_permission)
    assert tuple(signature.parameters.keys()) == ("user_role", "required_role")

    assert AuthService.check_permission("ADMIN", "OPERATOR") is True
    assert AuthService.check_permission("VIEWER", "ADMIN") is False


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


# =============================================================================
# Relocated from test_batch2_rx_event_fixups_and_tokens.py
# =============================================================================


# Relocated from test_batch2_rx_event_fixups_and_tokens.py — auth state contract
def test_auth_state_permission_contract_uses_private_helper_and_vars() -> None:
    assert not hasattr(AuthState, "has_permission")

    state = AuthState()
    state.is_authenticated = True
    state.user_role = "ADMIN"

    assert state._has_permission("ADMIN") is True
    assert state._has_permission("OPERATOR") is True
    assert state._has_permission("VIEWER") is True
    assert state.is_admin is True
    assert state.is_operator is True


@pytest.mark.anyio
async def test_check_session_timeout_no_longer_returns_bool() -> None:
    state = AuthState()
    state.is_authenticated = True
    state.last_activity = datetime.utcnow().isoformat()

    result = await AuthState.check_session_timeout.fn(state)

    assert result is None
    assert state.session_expired is False


# =============================================================================
# Relocated from test_batch3_unified_error_feedback.py — toast helpers
# =============================================================================


def _as_event_list(result: object) -> list[EventSpec]:
    if result is None:
        return []
    if isinstance(result, EventSpec):
        return [result]
    if isinstance(result, (tuple, list)):
        return [event for event in result if isinstance(event, EventSpec)]
    return []


def _event_args_map(event: EventSpec) -> dict[str, object]:
    args_map: dict[str, object] = {}
    for key_var, value in event.args:
        key = getattr(key_var, "_js_expr", "")
        if isinstance(key, str) and key:
            args_map[key] = value
    return args_map


def _is_toast_event(event: EventSpec, toast_kind: str | None = None) -> bool:
    args_map = _event_args_map(event)
    function_arg = args_map.get("function")
    function_expr = getattr(function_arg, "_js_expr", "")
    if "__toast" not in function_expr:
        return False
    if toast_kind is None:
        return True
    return f'"{toast_kind}"' in function_expr


def _is_redirect_event(event: EventSpec, path: str | None = None) -> bool:
    args_map = _event_args_map(event)
    if "path" not in args_map:
        return False
    if path is None:
        return True
    path_arg = args_map.get("path")
    return getattr(path_arg, "_var_value", None) == path


def _assert_toast_event(result: object, toast_kind: str | None = None) -> None:
    events = _as_event_list(result)
    assert events
    assert any(_is_toast_event(event, toast_kind=toast_kind) for event in events)


# Relocated from test_batch3_unified_error_feedback.py — auth error/toast tests


@pytest.mark.anyio
async def test_auth_login_error_keeps_inline_error_and_returns_error_toast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = AuthState()
    state.username = "bad-user"
    state.password = "bad-pass"

    monkeypatch.setattr(
        "kakumi_app.states.auth_state.AuthService.login_user",
        lambda username, password: (None, False, "Invalid username or password"),
    )

    result = await AuthState.login.fn(state)

    events = _as_event_list(result)
    assert events
    assert any(_is_toast_event(event, toast_kind="error") for event in events)
    assert not any(_is_redirect_event(event) for event in events)
    assert state.login_error == "Invalid username or password"
    assert state.is_logging_in is False


@pytest.mark.anyio
async def test_auth_login_success_returns_success_toast_then_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = AuthState()
    state.username = "admin"
    state.password = "StrongPass123!"

    fake_user = SimpleNamespace(
        id=99,
        username="admin",
        email="admin@test.dev",
        role="ADMIN",
        is_active=True,
    )
    monkeypatch.setattr(
        "kakumi_app.states.auth_state.AuthService.login_user",
        lambda username, password: (fake_user, False, ""),
    )

    result = await AuthState.login.fn(state)

    events = _as_event_list(result)
    assert events
    assert _is_toast_event(events[0], toast_kind="success")
    assert _is_redirect_event(events[1], path="/home")
    assert state.is_authenticated is True
    assert state.user_role == "ADMIN"
    assert state.username == ""
    assert state.password == ""
    assert state.login_error == ""
    assert state.is_logging_in is False


@pytest.mark.anyio
async def test_auth_login_success_sets_serializable_current_user_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = AuthState()
    state.username = "admin"
    state.password = "StrongPass123!"

    fake_user = SimpleNamespace(
        id=99,
        username="admin",
        email="admin@test.dev",
        role="ADMIN",
        is_active=True,
    )
    monkeypatch.setattr(
        "kakumi_app.states.auth_state.AuthService.login_user",
        lambda username, password: (fake_user, False, ""),
    )

    await AuthState.login.fn(state)

    assert isinstance(state.current_user, dict)
    assert state.current_user == {
        "id": 99,
        "username": "admin",
        "email": "admin@test.dev",
        "role": "ADMIN",
        "is_active": True,
    }


@pytest.mark.anyio
async def test_check_auth_does_not_redirect_authenticated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GIVEN user authenticated
    WHEN check_auth() called on /login on_load
    THEN should NOT redirect — user must always provide credentials
    """
    state = AuthState()

    def fake_load_user_from_stored(self) -> None:
        self.is_authenticated = True

    monkeypatch.setattr(AuthState, "_load_user_from_stored", fake_load_user_from_stored)

    result = await AuthState.check_auth.fn(state)

    assert result is None


@pytest.mark.anyio
async def test_check_change_password_access_redirects_to_home_when_no_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GIVEN user authenticated but needs_password_change=False
    WHEN check_change_password_access() called
    THEN redirect to /home
    """
    state = AuthState()
    state.is_authenticated = True
    state.needs_password_change = False

    result = await AuthState.check_change_password_access.fn(state)

    events = _as_event_list(result)
    assert events
    assert _is_redirect_event(events[0], path="/home")


@pytest.mark.anyio
async def test_auth_logout_returns_toast_and_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = AuthState()
    state.is_authenticated = True
    state.user_role = "ADMIN"
    state.login_error = "something"

    result = await AuthState.logout.fn(state)

    events = _as_event_list(result)
    assert events
    assert _is_toast_event(events[0], toast_kind="info")
    assert _is_redirect_event(events[1], path="/login")
    assert state.is_authenticated is False
    assert state.user_role == ""
    assert state.login_error == ""
    assert state.session_expired is False


@pytest.mark.anyio
async def test_auth_session_timeout_returns_warning_toast_and_redirect() -> None:
    state = AuthState()
    state.is_authenticated = True
    state.user_role = "OPERATOR"
    state.last_activity = "2000-01-01T00:00:00"

    result = await AuthState.check_session_timeout.fn(state)

    events = _as_event_list(result)
    assert events
    assert _is_toast_event(events[0], toast_kind="warning")
    assert _is_redirect_event(events[1], path="/login")
    assert state.is_authenticated is False
    assert state.user_role == ""
    assert state.session_expired is True


# =============================================================================
# Integration tests — from test_rbac_integration.py
# =============================================================================


def test_admin_page_redirect_on_insufficient_role() -> None:
    """GIVEN VIEWER navigating to admin page
    WHEN _has_permission("OPERATOR") is called
    THEN returns False (denied)
    """
    state = AuthState()
    state.is_authenticated = True
    state.user_role = "VIEWER"

    # Verify the gate check that drives the redirect
    assert state._has_permission("OPERATOR") is False
    assert state._has_permission("ADMIN") is False

    # For ADMIN role, the check passes
    state_admin = AuthState()
    state_admin.is_authenticated = True
    state_admin.user_role = "ADMIN"
    assert state_admin._has_permission("OPERATOR") is True

    # For OPERATOR role, the check also passes
    state_op = AuthState()
    state_op.is_authenticated = True
    state_op.user_role = "OPERATOR"
    assert state_op._has_permission("OPERATOR") is True


def test_permission_helper_admin_can_access_all() -> None:
    """ADMIN can access all lower/equal roles via helper path."""
    state = AuthState()
    state.is_authenticated = True
    state.user_role = "ADMIN"
    assert state._has_permission("ADMIN") is True
    assert state._has_permission("OPERATOR") is True
    assert state._has_permission("VIEWER") is True
    assert state.is_admin is True
    assert state.is_operator is True


def test_permission_helper_operator_can_access_operator_and_viewer() -> None:
    """OPERATOR can access OPERATOR/VIEWER but not ADMIN."""
    state = AuthState()
    state.is_authenticated = True
    state.user_role = "OPERATOR"
    assert state._has_permission("ADMIN") is False
    assert state._has_permission("OPERATOR") is True
    assert state._has_permission("VIEWER") is True
    assert state.is_admin is False
    assert state.is_operator is True


def test_permission_helper_viewer_can_only_access_viewer() -> None:
    """VIEWER can only access VIEWER."""
    state = AuthState()
    state.is_authenticated = True
    state.user_role = "VIEWER"
    assert state._has_permission("ADMIN") is False
    assert state._has_permission("OPERATOR") is False
    assert state._has_permission("VIEWER") is True
    assert state.is_admin is False
    assert state.is_operator is False


def test_permission_helper_unauthenticated_denied() -> None:
    """Unauthenticated users are denied regardless of role."""
    state = AuthState()
    state.user_role = "ADMIN"
    state.is_authenticated = False
    assert state._has_permission("VIEWER") is False
    assert state.is_admin is False
    assert state.is_operator is False
