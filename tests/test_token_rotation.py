"""
Tests for refresh token rotation logic.
"""

import pytest
import jwt
from datetime import datetime, timedelta
from kakumi_app.services.auth_service import AuthService, JWT_SECRET_KEY, JWT_ALGORITHM
from kakumi_app.models.user_model import User


@pytest.fixture
def test_user(db_session):
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


def test_refresh_token_invalidates_old(db_session, test_user):
    """Test that refresh token rotation blacklists the old token."""
    # Create a refresh token manually
    payload = {
        "sub": str(test_user.id),
        "exp": datetime.utcnow() + timedelta(days=1),
        "type": "refresh",
        "jti": "old-refresh-jti",
        "role": test_user.role,
    }
    old_refresh = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    # Call refresh_tokens
    new_access, new_refresh, error = AuthService.refresh_tokens(old_refresh)

    assert error == ""
    assert new_access is not None
    assert new_refresh is not None
    # Old refresh should be blacklisted
    assert AuthService.is_token_blacklisted(old_refresh)
