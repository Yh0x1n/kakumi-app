"""
Tests for account lockout logic (5 failed attempts = 15 min lockout).
"""

import pytest
from datetime import datetime, timedelta
from kakumi_app.services.auth_service import AuthService
from kakumi_app.models.user_model import User


@pytest.fixture
def test_user(db_session):
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


def test_account_unlocks_after_timeout(db_session, test_user):
    """Test that locked account auto-unlocks after timeout."""
    # Lock the account
    test_user.locked_until = datetime.utcnow() + timedelta(minutes=1)
    db_session.add(test_user)
    db_session.commit()

    # Should still be locked
    locked, _ = AuthService.is_account_locked(test_user)
    assert locked

    # Simulate timeout passed
    test_user.locked_until = datetime.utcnow() - timedelta(minutes=1)
    db_session.add(test_user)
    db_session.commit()

    # Should be unlocked now
    locked, _ = AuthService.is_account_locked(test_user)
    assert not locked
