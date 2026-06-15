"""Tests for RBAC admin page gates, sidebar role filtering, and protected_layout."""

from __future__ import annotations

import pytest
import reflex as rx

from kakumi_app.states.auth_state import AuthState
from kakumi_app.states.auth_state import DEV_AUTH_BYPASS


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
# SCENARIO: admin page accessible by ADMIN
# =============================================================================


def test_admin_page_accessible_by_admin() -> None:
    """GIVEN user with role ADMIN
    WHEN _has_permission("OPERATOR") called
    THEN returns True
    """
    state = _state_with_role("ADMIN")
    assert state._has_permission("OPERATOR") is True
    assert state._has_permission("ADMIN") is True


# =============================================================================
# SCENARIO: admin page denied for VIEWER
# =============================================================================


def test_admin_page_denied_for_viewer() -> None:
    """GIVEN user with role VIEWER
    WHEN _has_permission("OPERATOR") called
    THEN returns False
    """
    state = _state_with_role("VIEWER")
    assert state._has_permission("OPERATOR") is False
    assert state._has_permission("ADMIN") is False


# =============================================================================
# SCENARIO: admin page denied unauthenticated
# =============================================================================


def test_admin_page_denied_unauthenticated() -> None:
    """GIVEN user NOT authenticated
    WHEN _has_permission("OPERATOR") called
    THEN returns False
    """
    state = _state_with_role("VIEWER", authenticated=False)
    assert state._has_permission("VIEWER") is False
    assert state._has_permission("OPERATOR") is False
    assert state._has_permission("ADMIN") is False


# =============================================================================
# SCENARIO: sidebar hides admin links for VIEWER
# =============================================================================


def test_sidebar_hides_admin_links_for_viewer() -> None:
    """GIVEN user with role VIEWER
    THEN _has_permission("OPERATOR") is False
    AND admin sidebar links NOT accessible
    """
    state = _state_with_role("VIEWER")
    assert state._has_permission("OPERATOR") is False

    state_admin = _state_with_role("ADMIN")
    assert state_admin._has_permission("OPERATOR") is True

    # The sidebar component uses rx.cond(AuthState._has_permission("OPERATOR"), ...)
    # so we verify the underlying check works for both roles
    # VIEWER: hidden (check returns False)
    # ADMIN: visible (check returns True)


# =============================================================================
# SCENARIO: protected_layout with required_role param
# =============================================================================


def test_protected_layout_gates_by_role() -> None:
    """GIVEN protected_layout with required_role="ADMIN"
    WHEN user has role OPERATOR
    THEN _has_permission("ADMIN") returns False
    WHEN user has role ADMIN
    THEN _has_permission("ADMIN") returns True
    """
    state_op = _state_with_role("OPERATOR")
    assert state_op._has_permission("ADMIN") is False

    state_admin = _state_with_role("ADMIN")
    assert state_admin._has_permission("ADMIN") is True

    # protected_layout renders the rx.cond at render time
    # The gate check is AuthState._has_permission(required_role)
    # which we verify above


# =============================================================================
# SCENARIO: teams_page and export_page content gated by OPERATOR
# =============================================================================


def test_team_page_gate_operator_check() -> None:
    """GIVEN teams_page has rx.cond gate for OPERATOR
    WHEN checking _has_permission("OPERATOR")
    THEN VIEWER returns False, OPERATOR returns True, ADMIN returns True
    """
    viewer = _state_with_role("VIEWER")
    assert viewer._has_permission("OPERATOR") is False

    operator = _state_with_role("OPERATOR")
    assert operator._has_permission("OPERATOR") is True

    admin = _state_with_role("ADMIN")
    assert admin._has_permission("OPERATOR") is True


# =============================================================================
# SCENARIO: export page gate
# =============================================================================


def test_export_page_gate_operator_check() -> None:
    """GIVEN export_page has rx.cond gate for OPERATOR
    WHEN checking _has_permission("OPERATOR")
    THEN VIEWER denied, OPERATOR/ADMIN allowed
    """
    viewer = _state_with_role("VIEWER")
    assert viewer._has_permission("OPERATOR") is False

    operator = _state_with_role("OPERATOR")
    assert operator._has_permission("OPERATOR") is True

    admin = _state_with_role("ADMIN")
    assert admin._has_permission("OPERATOR") is True


# =============================================================================
# SCENARIO: DEV_AUTH_BYPASS skips gates
# =============================================================================


def test_dev_bypass_defaults_to_operator() -> None:
    """GIVEN DEV_AUTH_BYPASS is configured
    WHEN _load_user_from_token runs
    THEN role is OPERATOR and _has_permission("OPERATOR") is True
    """
    state = AuthState()
    state._load_user_from_token()

    if DEV_AUTH_BYPASS:
        assert state.user_role == "OPERATOR"
        assert state._has_permission("OPERATOR") is True
        assert state._has_permission("ADMIN") is False
        assert state.is_authenticated is True
    else:
        # Not bypassed — no token means unauthenticated
        assert state.is_authenticated is False


# =============================================================================
# SCENARIO: protected_layout renders denied message (logic check)
# =============================================================================


def test_protected_layout_denied_check() -> None:
    """GIVEN protected_layout with required_role parameter
    WHEN user lacks the required role
    THEN denied message is shown (verified via check logic)
    """
    # Simulate VIEWER trying to access OPERATOR-gated layout
    state = _state_with_role("VIEWER")
    has_perm = state._has_permission("OPERATOR")
    assert has_perm is False

    # The rx.cond in protected_layout:
    # rx.cond(auth_state._has_permission(required_role), content, denied_message)
    # When has_perm is False, the denied branch renders
    # When has_perm is True, the content branch renders
    # We verify the underlying boolean logic matches


def test_protected_layout_allowed_check() -> None:
    """GIVEN protected_layout with required_role="OPERATOR"
    WHEN user has ADMIN role
    THEN content is rendered (check returns True)
    """
    state = _state_with_role("ADMIN")
    has_perm = state._has_permission("OPERATOR")
    assert has_perm is True

    state = _state_with_role("OPERATOR")
    has_perm = state._has_permission("OPERATOR")
    assert has_perm is True
