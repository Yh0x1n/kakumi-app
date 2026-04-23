"""Tests for RBAC in AuthState using AuthService as source of truth."""

from kakumi_app.states.auth_state import AuthState


def test_has_permission_admin_can_access_all() -> None:
    """ADMIN can access all lower/equal roles via AuthService path."""
    state = AuthState()
    state.is_authenticated = True
    state.user_role = "ADMIN"
    assert state.has_permission("ADMIN") is True
    assert state.has_permission("OPERATOR") is True
    assert state.has_permission("VIEWER") is True


def test_has_permission_operator_can_access_operator_and_viewer() -> None:
    """OPERATOR can access OPERATOR/VIEWER but not ADMIN."""
    state = AuthState()
    state.is_authenticated = True
    state.user_role = "OPERATOR"
    assert state.has_permission("ADMIN") is False
    assert state.has_permission("OPERATOR") is True
    assert state.has_permission("VIEWER") is True


def test_has_permission_viewer_can_only_access_viewer() -> None:
    """VIEWER can only access VIEWER."""
    state = AuthState()
    state.is_authenticated = True
    state.user_role = "VIEWER"
    assert state.has_permission("ADMIN") is False
    assert state.has_permission("OPERATOR") is False
    assert state.has_permission("VIEWER") is True


def test_has_permission_unauthenticated_denied() -> None:
    """Unauthenticated users are denied regardless of role."""
    state = AuthState()
    state.user_role = "ADMIN"
    state.is_authenticated = False
    assert state.has_permission("VIEWER") is False
