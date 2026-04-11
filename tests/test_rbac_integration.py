"""
Tests for RBAC in AuthState.
"""

import pytest
from datetime import datetime, timedelta
from kakumi_app.states.auth_state import AuthState


def test_require_role_admin_can_access_all():
    """Test that ADMIN can access all roles."""
    state = AuthState()
    state.user_role = "ADMIN"
    assert state.require_role("ADMIN") == True
    assert state.require_role("OPERATOR") == True
    assert state.require_role("VIEWER") == True


def test_require_role_operator_can_access_operator_and_viewer():
    """Test that OPERATOR can access OPERATOR and VIEWER but not ADMIN."""
    state = AuthState()
    state.user_role = "OPERATOR"
    assert state.require_role("ADMIN") == False
    assert state.require_role("OPERATOR") == True
    assert state.require_role("VIEWER") == True


def test_require_role_viewer_can_only_access_viewer():
    """Test that VIEWER can only access VIEWER."""
    state = AuthState()
    state.user_role = "VIEWER"
    assert state.require_role("ADMIN") == False
    assert state.require_role("OPERATOR") == False
    assert state.require_role("VIEWER") == True


def test_require_role_unauthenticated():
    """Test that unauthenticated user cannot access anything."""
    state = AuthState()
    state.user_role = ""
    assert state.require_role("VIEWER") == False
