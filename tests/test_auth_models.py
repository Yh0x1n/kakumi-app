"""
Tests for LoginAttempt and TokenBlacklist models.
"""

import pytest
from datetime import datetime, timedelta
from kakumi_app.models.login_attempt import LoginAttempt
from kakumi_app.models.token_blacklist import TokenBlacklist


def test_login_attempt_creation(db_session):
    """Test creating a LoginAttempt record."""
    attempt = LoginAttempt(
        username="testuser",
        ip_address="192.168.1.1",
        user_agent="pytest",
        was_successful=True,
        failure_reason=None,
    )
    db_session.add(attempt)
    db_session.commit()
    assert attempt.id is not None
    assert attempt.username == "testuser"
    assert attempt.was_successful == True


def test_login_attempt_failure_reason(db_session):
    """Test recording failed login attempts."""
    for reason in ["INVALID_PASS", "USER_NOT_FOUND", "ACCOUNT_LOCKED"]:
        attempt = LoginAttempt(
            username="testuser",
            ip_address="192.168.1.1",
            user_agent="pytest",
            was_successful=False,
            failure_reason=reason,
        )
        db_session.add(attempt)
        db_session.commit()
        assert attempt.failure_reason == reason


def test_token_blacklist_creation(db_session):
    """Test creating a TokenBlacklist entry."""
    entry = TokenBlacklist(
        token_jti="test-jti-123",
        user_id=1,
        token_type="access",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        reason="LOGOUT",
    )
    db_session.add(entry)
    db_session.commit()
    assert entry.id is not None
    assert entry.token_jti == "test-jti-123"
