"""Tests for RBAC in AuthState using AuthService as source of truth."""

from kakumi_app.states.auth_state import AuthState


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
