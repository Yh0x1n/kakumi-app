"""Tests for force password change flow: migration, auth service, auth state."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.command import upgrade as alembic_upgrade
from alembic.command import downgrade as alembic_downgrade
from alembic.config import Config as AlembicConfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# =============================================================================
# Toast/event helpers (previously imported from test_batch3_unified_error_feedback.py)
# =============================================================================


import reflex as rx
from reflex.event import EventSpec


def _as_event_list(result: object) -> list[EventSpec]:
    if result is None:
        return []
    if isinstance(result, EventSpec):
        return [result]
    if isinstance(result, (tuple, list)):
        return [event for event in result if isinstance(event, EventSpec)]
    return []


def _is_toast_event(event: EventSpec, toast_kind: str | None = None) -> bool:
    def _event_args_map(e: EventSpec) -> dict[str, object]:
        args_map: dict[str, object] = {}
        for key_var, value in e.args:
            key = getattr(key_var, "_js_expr", "")
            if isinstance(key, str) and key:
                args_map[key] = value
        return args_map

    args_map = _event_args_map(event)
    function_arg = args_map.get("function")
    function_expr = getattr(function_arg, "_js_expr", "")
    if "__toast" not in function_expr:
        return False
    if toast_kind is None:
        return True
    return f'"{toast_kind}"' in function_expr


def _is_redirect_event(event: EventSpec, path: str | None = None) -> bool:
    def _event_args_map(e: EventSpec) -> dict[str, object]:
        args_map: dict[str, object] = {}
        for key_var, value in e.args:
            key = getattr(key_var, "_js_expr", "")
            if isinstance(key, str) and key:
                args_map[key] = value
        return args_map

    args_map = _event_args_map(event)
    if "path" not in args_map:
        return False
    if path is None:
        return True
    path_arg = args_map.get("path")
    return getattr(path_arg, "_var_value", None) == path


@pytest.fixture(scope="function")
def alembic_cfg() -> AlembicConfig:
    """Create alembic config pointing to a temp SQLite DB."""
    fd, db_path = tempfile.mkstemp(suffix=".db", prefix="kakumi-migration-test-")
    import os

    os.close(fd)

    cfg = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    yield cfg
    cfg = None
    os.unlink(db_path)


# =============================================================================
# SCENARIO: migration applies
# =============================================================================


def test_migration_adds_force_password_change_column(
    alembic_cfg: AlembicConfig,
) -> None:
    """GIVEN fresh DB at head 9a8b7c6d5e4f
    WHEN alembic upgrade head runs new revision
    THEN users has column force_password_change (BOOLEAN, NOT NULL, server_default='0')
    """
    # Apply all migrations up to current head
    alembic_upgrade(alembic_cfg, "9a8b7c6d5e4f")

    # Inspect schema before the new migration
    db_url = alembic_cfg.get_main_option("sqlalchemy.url")
    engine = sa.create_engine(db_url)
    inspector = sa.inspect(engine)
    columns_before = {col["name"]: col for col in inspector.get_columns("users")}
    assert "force_password_change" not in columns_before, (
        "Column should NOT exist before migration"
    )
    engine.dispose()

    # Apply the new migration
    alembic_upgrade(alembic_cfg, "a1b2c3d4e5f6")

    # Inspect schema after migration
    engine = sa.create_engine(db_url)
    inspector = sa.inspect(engine)
    columns_after = {col["name"]: col for col in inspector.get_columns("users")}
    assert "force_password_change" in columns_after, (
        "Column should exist after migration"
    )
    col = columns_after["force_password_change"]
    assert col["nullable"] is False, "Column should be NOT NULL"
    engine.dispose()


# =============================================================================
# SCENARIO: migration rollback
# =============================================================================


def test_migration_rollback_drops_column(alembic_cfg: AlembicConfig) -> None:
    """GIVEN schema at new revision
    WHEN alembic downgrade -1 runs
    THEN users table drops force_password_change column
    AND no data loss for remaining columns
    """
    # Apply the new migration
    alembic_upgrade(alembic_cfg, "a1b2c3d4e5f6")

    db_url = alembic_cfg.get_main_option("sqlalchemy.url")
    engine = sa.create_engine(db_url)
    inspector = sa.inspect(engine)
    columns_after_up = {col["name"]: col for col in inspector.get_columns("users")}
    assert "force_password_change" in columns_after_up, (
        "Column should exist after upgrade"
    )
    engine.dispose()

    # Rollback
    alembic_downgrade(alembic_cfg, "-1")

    # Verify column is gone
    engine = sa.create_engine(db_url)
    inspector = sa.inspect(engine)
    columns_after_down = {col["name"]: col for col in inspector.get_columns("users")}
    assert "force_password_change" not in columns_after_down, (
        "Column should be gone after rollback"
    )
    # Verify existing columns preserved
    assert "id" in columns_after_down
    assert "username" in columns_after_down
    assert "password_hash" in columns_after_down
    engine.dispose()


# =============================================================================
# AuthService: login_user returns 4-tuple with force_password_change
# =============================================================================


def test_login_user_returns_3tuple_on_success(db_session) -> None:
    """GIVEN user with force_password_change=True
    WHEN login_user succeeds
    THEN returns (user, True, "")
    """
    from kakumi_app.models.user_model import User, UserRole
    from kakumi_app.services.auth_service import AuthService

    user = User(
        username="force-change-user",
        email="force@test.dev",
        password_hash=AuthService.hash_password("StrongPass123!"),
        full_name="Force Change User",
        role=UserRole.OPERATOR.value,
        is_active=True,
        force_password_change=True,
    )
    db_session.add(user)
    db_session.commit()

    result_user, force_change, error = AuthService.login_user(
        "force-change-user", "StrongPass123!"
    )
    assert result_user is not None, "Should return user"
    assert result_user.id == user.id
    assert force_change is True, "Should return force_change=True"
    assert error == "", "Error should be empty"


def test_login_user_returns_force_change_false_when_not_set(db_session) -> None:
    """GIVEN user with force_password_change=False
    WHEN login_user succeeds
    THEN returns (token, refresh, False, "")
    """
    from kakumi_app.models.user_model import User, UserRole
    from kakumi_app.services.auth_service import AuthService

    user = User(
        username="normal-user",
        email="normal@test.dev",
        password_hash=AuthService.hash_password("StrongPass123!"),
        full_name="Normal User",
        role=UserRole.OPERATOR.value,
        is_active=True,
        force_password_change=False,
    )
    db_session.add(user)
    db_session.commit()

    result_user, force_change, error = AuthService.login_user(
        "normal-user", "StrongPass123!"
    )
    assert result_user is not None
    assert result_user.id == user.id
    assert force_change is False
    assert error == ""


def test_login_user_returns_3tuple_on_failure() -> None:
    """GIVEN invalid credentials
    WHEN login_user fails
    THEN returns (None, False, "error message")
    """
    from kakumi_app.services.auth_service import AuthService

    result_user, force_change, error = AuthService.login_user(
        "nonexistent", "wrongpass"
    )
    assert result_user is None
    assert force_change is False, "force_change should be False for failed login"
    assert error != "", "Should have error message"


# =============================================================================
# AuthService: change_password
# =============================================================================


def test_change_password_validates_strength(db_session) -> None:
    """GIVEN user with known password
    WHEN change_password called with weak new password
    THEN returns (False, strength_error)
    """
    from kakumi_app.models.user_model import User, UserRole
    from kakumi_app.services.auth_service import AuthService

    user = User(
        username="strength-test",
        email="strength@test.dev",
        password_hash=AuthService.hash_password("StrongPass123!"),
        full_name="Strength Test",
        role=UserRole.OPERATOR.value,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    success, error = AuthService.change_password(
        user_id=user.id,
        old_password="StrongPass123!",
        new_password="short",
    )
    assert success is False
    assert "8 characters" in error or "min" in error.lower()


def test_change_password_rejects_wrong_old_password(db_session) -> None:
    """GIVEN user's current password hash matches old_pw
    WHEN change_password called with wrong old password
    THEN returns (False, "Current password is incorrect")
    """
    from kakumi_app.models.user_model import User, UserRole
    from kakumi_app.services.auth_service import AuthService

    user = User(
        username="wrong-old-pw",
        email="wrong-old@test.dev",
        password_hash=AuthService.hash_password("StrongPass123!"),
        full_name="Wrong Old PW",
        role=UserRole.OPERATOR.value,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    success, error = AuthService.change_password(
        user_id=user.id,
        old_password="WrongOldPass123!",
        new_password="NewStrongPass456!",
    )
    assert success is False
    assert "Current password is incorrect" in error


def test_change_password_clears_flag(db_session) -> None:
    """GIVEN user with force_password_change=True
    WHEN change_password succeeds
    THEN force_password_change=False in DB
    """
    from kakumi_app.models.user_model import User, UserRole
    from kakumi_app.services.auth_service import AuthService

    user = User(
        username="clear-flag",
        email="clear-flag@test.dev",
        password_hash=AuthService.hash_password("OldStrongPass123!"),
        full_name="Clear Flag",
        role=UserRole.OPERATOR.value,
        is_active=True,
        force_password_change=True,
    )
    db_session.add(user)
    db_session.commit()

    success, error = AuthService.change_password(
        user_id=user.id,
        old_password="OldStrongPass123!",
        new_password="NewStrongPass456!",
    )
    assert success is True
    assert error == ""

    # Verify flag cleared in DB (expire session to bypass cache)
    db_session.expire_all()
    fresh = db_session.get(User, user.id)
    assert fresh is not None
    assert fresh.force_password_change is False


def test_change_password_updates_hash(db_session) -> None:
    """GIVEN user with known password
    WHEN change_password succeeds
    THEN password_hash is updated and old password no longer works
    """
    import bcrypt
    from kakumi_app.models.user_model import User, UserRole
    from kakumi_app.services.auth_service import AuthService

    user = User(
        username="hash-update",
        email="hash-update@test.dev",
        password_hash=AuthService.hash_password("OldStrongPass123!"),
        full_name="Hash Update",
        role=UserRole.OPERATOR.value,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    success, error = AuthService.change_password(
        user_id=user.id,
        old_password="OldStrongPass123!",
        new_password="NewStrongPass456!",
    )
    assert success is True

    db_session.expire_all()
    fresh = db_session.get(User, user.id)
    assert fresh is not None
    # Old password should NOT work
    assert not bcrypt.checkpw(
        "OldStrongPass123!".encode(), fresh.password_hash.encode()
    )
    # New password SHOULD work
    assert bcrypt.checkpw("NewStrongPass456!".encode(), fresh.password_hash.encode())


def test_change_password_user_not_found(db_session) -> None:
    """GIVEN no user with given user_id
    WHEN change_password called
    THEN returns (False, "User not found")
    """
    from kakumi_app.services.auth_service import AuthService

    success, error = AuthService.change_password(
        user_id=99999,
        old_password="anything",
        new_password="NewStrongPass456!",
    )
    assert success is False
    assert "User not found" in error


# =============================================================================
# AuthState: login with force_change redirects to /change-password
# =============================================================================


@pytest.mark.anyio
async def test_login_redirects_to_change_password_when_flag_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GIVEN login_user returns (user, True, "")
    WHEN AuthState.login executes
    THEN needs_password_change=True and redirect to /change-password
    """
    from types import SimpleNamespace
    from kakumi_app.states.auth_state import AuthState

    fake_user = SimpleNamespace(
        id=1, username="admin", email="", role="ADMIN", is_active=True
    )
    state = AuthState()
    state.username = "admin"
    state.password = "StrongPass123!"

    monkeypatch.setattr(
        "kakumi_app.states.auth_state.AuthService.login_user",
        lambda username, password: (fake_user, True, ""),
    )

    result = await AuthState.login.fn(state)

    assert state.needs_password_change is True
    assert state.is_logging_in is False

    events = _as_event_list(result)
    assert events
    assert any(_is_toast_event(event, toast_kind="warning") for event in events)
    assert any(_is_redirect_event(event, path="/change-password") for event in events)


@pytest.mark.anyio
async def test_login_does_not_redirect_to_change_password_when_flag_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GIVEN login_user returns (user, False, "")
    WHEN AuthState.login executes
    THEN needs_password_change=False and redirect to /
    """
    from types import SimpleNamespace
    from kakumi_app.states.auth_state import AuthState

    fake_user = SimpleNamespace(
        id=1, username="admin", email="", role="ADMIN", is_active=True
    )
    state = AuthState()
    state.username = "admin"
    state.password = "StrongPass123!"

    monkeypatch.setattr(
        "kakumi_app.states.auth_state.AuthService.login_user",
        lambda username, password: (fake_user, False, ""),
    )

    def fake_load_user(self) -> None:
        self.is_authenticated = True
        self.user_role = "ADMIN"
        self.current_user = {
            "id": 1,
            "username": "admin",
            "role": "ADMIN",
            "is_active": True,
        }

    monkeypatch.setattr(AuthState, "_load_user_from_stored", fake_load_user)

    result = await AuthState.login.fn(state)

    assert state.needs_password_change is False

    events = _as_event_list(result)
    assert events
    assert _is_toast_event(events[0], toast_kind="success")
    assert _is_redirect_event(events[1], path="/home")


@pytest.mark.anyio
async def test_change_password_clears_needs_password_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GIVEN needs_password_change=True, user authenticated
    WHEN handle_change_password called with valid form_data
    THEN needs_password_change=False, toast success, redirect /
    """
    from kakumi_app.states.auth_state import AuthState

    state = AuthState()
    state.needs_password_change = True
    state.is_authenticated = True
    state.current_user = {"id": 1, "username": "admin", "role": "ADMIN"}
    state.cp_current_password = "OldPass123!"
    state.cp_new_password = "NewStrongPass456!"
    state.cp_confirm_password = "NewStrongPass456!"

    monkeypatch.setattr(
        "kakumi_app.states.auth_state.AuthService.change_password",
        lambda user_id, old_password, new_password: (True, ""),
    )

    monkeypatch.setattr(
        "kakumi_app.states.auth_state.AuthService.login_user",
        lambda username, password: (
            "new-token",
            "new-refresh",
            False,
            "",
        ),
    )

    result = await AuthState.handle_change_password.fn(state)

    assert state.needs_password_change is False
    assert state.cp_current_password == ""
    assert state.cp_new_password == ""
    assert state.cp_confirm_password == ""

    events = _as_event_list(result)
    assert events
    assert _is_toast_event(events[0], toast_kind="success")
    assert _is_redirect_event(events[1], path="/home")


@pytest.mark.anyio
async def test_change_password_stays_on_page_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GIVEN handle_change_password called with wrong old password
    WHEN AuthService.change_password returns error
    THEN toast error, stays on page, needs_password_change remains True
    """
    from kakumi_app.states.auth_state import AuthState

    state = AuthState()
    state.needs_password_change = True
    state.is_authenticated = True
    state.current_user = {"id": 1, "username": "admin", "role": "ADMIN"}
    state.cp_current_password = "WrongOldPass123!"
    state.cp_new_password = "NewStrongPass456!"
    state.cp_confirm_password = "NewStrongPass456!"

    monkeypatch.setattr(
        "kakumi_app.states.auth_state.AuthService.change_password",
        lambda user_id, old_password, new_password: (
            False,
            "Current password is incorrect",
        ),
    )

    result = await AuthState.handle_change_password.fn(state)

    assert state.needs_password_change is True, "Flag should remain True on error"
    assert state.cp_error == "Current password is incorrect"

    events = _as_event_list(result)
    assert events
    assert _is_toast_event(events[0], toast_kind="error")


@pytest.mark.anyio
async def test_change_password_mismatch_returns_error() -> None:
    """GIVEN new_password != confirm_password
    WHEN handle_change_password called
    THEN toast error, no call to AuthService
    """
    from kakumi_app.states.auth_state import AuthState

    state = AuthState()
    state.needs_password_change = True
    state.is_authenticated = True
    state.current_user = {"id": 1, "username": "admin"}
    state.cp_current_password = "OldPass123!"
    state.cp_new_password = "NewStrongPass456!"
    state.cp_confirm_password = "DifferentPass789!"

    result = await AuthState.handle_change_password.fn(state)

    assert state.cp_error == "Passwords do not match"
    assert state.needs_password_change is True

    events = _as_event_list(result)
    assert events
    assert _is_toast_event(events[0], toast_kind="error")


def test_needs_password_change_default_false() -> None:
    """GIVEN fresh AuthState
    THEN needs_password_change is False
    """
    from kakumi_app.states.auth_state import AuthState

    state = AuthState()
    assert state.needs_password_change is False


def test_clear_auth_session_resets_needs_password_change() -> None:
    """GIVEN needs_password_change=True
    WHEN _clear_auth_session called
    THEN needs_password_change=False
    """
    from kakumi_app.states.auth_state import AuthState

    state = AuthState()
    state.needs_password_change = True
    state.cp_error = "some error"
    state._clear_auth_session()
    assert state.needs_password_change is False
    assert state.cp_error == ""


@pytest.mark.anyio
async def test_create_initial_admin_sets_force_password_change(db_session) -> None:
    """GIVEN no users in DB
    WHEN AuthState.create_initial_admin runs from env vars
    THEN created user has force_password_change=True in DB
    """
    import os
    from kakumi_app.models.user_model import User
    from kakumi_app.states.auth_state import AuthState

    # Ensure no users exist — db_session is isolated per test
    admin_username = "test-create-admin"
    admin_password = "AdminSetupPass123!"
    admin_email = "create-admin@test.dev"
    admin_full_name = "Create Admin Test"

    os.environ["ADMIN_USERNAME"] = admin_username
    os.environ["ADMIN_PASSWORD"] = admin_password
    os.environ["ADMIN_EMAIL"] = admin_email
    os.environ["ADMIN_FULL_NAME"] = admin_full_name

    state = AuthState()
    state.admin_created = False

    # Run create_initial_admin

    # Mock the password check so the env default "admin123" passes strength
    # We already set strong passwords via env
    from sqlmodel import select

    # First make sure there are NO users in DB
    with rx.session() as session:
        existing = session.exec(select(User)).all()
        assert len(existing) == 0, f"Expected no users, found {len(existing)}"

    await AuthState.create_initial_admin.fn(state)

    assert state.admin_created is True

    # Verify user has force_password_change=True
    with rx.session() as session:
        user = session.exec(select(User).where(User.username == admin_username)).first()
    assert user is not None, "Admin user should be created"
    assert user.force_password_change is True, (
        "Initial admin should have force_password_change=True"
    )

    # Clean up env
    del os.environ["ADMIN_USERNAME"]
    del os.environ["ADMIN_PASSWORD"]
    del os.environ["ADMIN_EMAIL"]
    del os.environ["ADMIN_FULL_NAME"]


def test_login_user_3tuple_shape_on_error() -> None:
    """GIVEN login_user called with bad password
    THEN return has consistent 3-tuple shape
    """
    from kakumi_app.services.auth_service import AuthService

    result = AuthService.login_user("does-not-exist", "bad-password")
    assert isinstance(result, tuple)
    assert len(result) == 3
    assert result[0] is None  # user
    assert result[1] is False  # force_password_change
    assert result[2] != ""  # error_message
