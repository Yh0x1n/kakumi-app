"""
Tests for AuthService: lockout, blacklist, password strength, refresh token rotation.

Merged from:
  - test_authservice_phase2.py (backbone)
  - test_lockout_logic.py
  - test_token_rotation.py
  - test_password_validation.py
"""

import pytest
from datetime import datetime, timedelta
from kakumi_app.services.auth_service import AuthService
from kakumi_app.models.user_model import User


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture()
def user_with_password(db_session):
    """User fixture from test_authservice_phase2.py."""
    user = User(
        username="lockuser",
        email="lockuser@test.com",
        password_hash=AuthService.hash_password("ValidPass123!"),
        full_name="Lock Test",
        role="ADMIN",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def lockout_user(db_session):
    """User fixture from test_lockout_logic.py."""
    user = User(
        username="locktest",
        email="locktest@test.com",
        password_hash=AuthService.hash_password("ValidPass123!"),
        full_name="Lock Test User",
        role="OPERATOR",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def token_user(db_session):
    """User fixture from test_token_rotation.py."""
    user = User(
        username="tokentest",
        email="tokentest@test.com",
        password_hash=AuthService.hash_password("ValidPass123!"),
        full_name="Token Test User",
        role="OPERATOR",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# =============================================================================
# Password strength — from test_authservice_phase2.py and test_password_validation.py
# =============================================================================


def test_password_strength_validation():
    """Test password strength validation with various weak/strong passwords."""
    weak_pwds = ["short", "noupper123!", "NOLOWER123!", "Noupper!", "Strongbutn0spcl"]
    for pwd in weak_pwds:
        ok, msg = AuthService.validate_password_strength(pwd)
        assert not ok
        assert "min" in msg or "uppercase" in msg or "number" in msg or "special" in msg
    assert AuthService.validate_password_strength("StrongPwd1!")[0]


@pytest.mark.parametrize(
    "password,should_pass",
    [
        ("short", False),  # Too short
        ("noupper123!", False),  # No uppercase
        ("NOLOWER123!", False),  # No lowercase
        ("Noupper!", False),  # No number
        ("Strongbutn0spcl", False),  # No special char
        ("ValidPass1!", True),  # Valid
        ("MyStr0ngP@ss", True),  # Valid
        ("Abc123!@#", True),  # Valid (8 chars exactly)
    ],
)
def test_password_strength(password, should_pass):
    """Parameterized password strength test from test_password_validation.py."""
    is_valid, _ = AuthService.validate_password_strength(password)
    assert is_valid == should_pass


# =============================================================================
# Lockout logic — from test_authservice_phase2.py and test_lockout_logic.py
# =============================================================================


def test_record_login_attempt_and_lockout(db_session, user_with_password):
    """5 failed attempts should lock account; unlock after timeout passes."""
    ip = "1.2.3.4"
    agent = "pytest"
    # fail 5 times
    for i in range(5):
        AuthService.record_login_attempt(
            user_with_password.username, ip, agent, False, reason="INVALID_PASS"
        )
    user = AuthService.get_user_by_username(user_with_password.username)
    locked, unlock_at = AuthService.is_account_locked(user)
    assert locked
    assert unlock_at > datetime.utcnow()
    # Account should auto-unlock after 15min
    user_db = db_session.get(User, user_with_password.id)
    user_db.locked_until = datetime.utcnow() - timedelta(minutes=1)
    db_session.commit()
    user = AuthService.get_user_by_username(user_with_password.username)
    locked, _ = AuthService.is_account_locked(user)
    assert not locked


def test_account_unlocks_after_timeout(db_session, lockout_user):
    """Test that locked account auto-unlocks after timeout (from test_lockout_logic.py)."""
    # Lock the account
    lockout_user.locked_until = datetime.utcnow() + timedelta(minutes=1)
    db_session.add(lockout_user)
    db_session.commit()

    # Should still be locked
    locked, _ = AuthService.is_account_locked(lockout_user)
    assert locked

    # Simulate timeout passed
    lockout_user.locked_until = datetime.utcnow() - timedelta(minutes=1)
    db_session.add(lockout_user)
    db_session.commit()

    # Should be unlocked now
    locked, _ = AuthService.is_account_locked(lockout_user)
    assert not locked


def test_reset_failed_attempts(db_session, user_with_password):
    """Failed attempts counter should reset to 0."""
    AuthService.record_login_attempt(
        user_with_password.username, "ip", "agent", False, reason="INVALID_PASS"
    )
    AuthService.record_login_attempt(
        user_with_password.username, "ip", "agent", False, reason="INVALID_PASS"
    )
    user = AuthService.get_user_by_username(user_with_password.username)
    assert user.failed_attempts == 2
    AuthService.reset_failed_attempts(user)
    user = AuthService.get_user_by_username(user_with_password.username)
    assert user.failed_attempts == 0


# =============================================================================
# Token blacklist — from test_authservice_phase2.py
# =============================================================================


# =============================================================================
# Token rotation — from test_authservice_phase2.py and test_token_rotation.py
# =============================================================================
