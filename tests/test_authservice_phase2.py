"""
Tests for AuthService Phase 2: Lockout, Blacklist, Password Strength, Refresh
"""

import pytest
import string
import time
from datetime import datetime, timedelta
import jwt
from kakumi_app.services.auth_service import AuthService, JWT_SECRET_KEY, JWT_ALGORITHM
from kakumi_app.models.user_model import User
from kakumi_app.models.token_blacklist import TokenBlacklist
from kakumi_app.models.login_attempt import LoginAttempt
import reflex as rx


@pytest.fixture()
def user_with_password(db_session):
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


def test_password_strength_validation():
    weak_pwds = ["short", "noupper123!", "NOLOWER123!", "Noupper!", "Strongbutn0spcl"]
    for pwd in weak_pwds:
        ok, msg = AuthService.validate_password_strength(pwd)
        assert not ok
        assert "min" in msg or "uppercase" in msg or "number" in msg or "special" in msg
    assert AuthService.validate_password_strength("StrongPwd1!")[0]


def test_record_login_attempt_and_lockout(db_session, user_with_password):
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


def test_reset_failed_attempts(db_session, user_with_password):
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


def test_blacklist_token_and_check(db_session, user_with_password):
    payload = {
        "sub": str(user_with_password.id),
        "exp": datetime.utcnow() + timedelta(minutes=10),
        "type": "access",
        "jti": "jwtidtest123",
        "role": user_with_password.role,
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    AuthService.blacklist_token(token, user_with_password.id, reason="LOGOUT")
    assert AuthService.is_token_blacklisted(token)


def test_refresh_tokens_rotates(db_session, user_with_password):
    # issue refresh token
    payload = {
        "sub": str(user_with_password.id),
        "exp": datetime.utcnow() + timedelta(days=1),
        "type": "refresh",
        "jti": "refreshjti1",
        "role": user_with_password.role,
    }
    refresh = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    access, new_refresh, err = AuthService.refresh_tokens(refresh)
    assert access is not None and new_refresh is not None and not err
    # Old refresh must now be blacklisted
    assert AuthService.is_token_blacklisted(refresh)
