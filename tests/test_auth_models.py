"""
Collapsed tests for LoginAttempt and TokenBlacklist models.

Replaces 3 separate tests with 1 parametrized test covering
LoginAttempt creation, LoginAttempt failure reason, and TokenBlacklist creation.
"""

import pytest
from datetime import datetime, timedelta
from kakumi_app.models.login_attempt import LoginAttempt
from kakumi_app.models.token_blacklist import TokenBlacklist


@pytest.mark.parametrize(
    ("model_factory", "assertions"),
    [
        pytest.param(
            lambda db: LoginAttempt(
                username="testuser",
                ip_address="192.168.1.1",
                user_agent="pytest",
                was_successful=True,
                failure_reason=None,
            ),
            [
                lambda obj: obj.id is not None,
                lambda obj: obj.username == "testuser",
                lambda obj: obj.was_successful is True,
            ],
            id="login_attempt_creation",
        ),
        pytest.param(
            lambda db: LoginAttempt(
                username="testuser",
                ip_address="192.168.1.1",
                user_agent="pytest",
                was_successful=False,
                failure_reason="INVALID_PASS",
            ),
            [
                lambda obj: obj.failure_reason == "INVALID_PASS",
            ],
            id="login_attempt_failure_reason",
        ),
        pytest.param(
            lambda db: TokenBlacklist(
                token_jti="test-jti-123",
                user_id=1,
                token_type="access",
                expires_at=datetime.utcnow() + timedelta(hours=1),
                reason="LOGOUT",
            ),
            [
                lambda obj: obj.id is not None,
                lambda obj: obj.token_jti == "test-jti-123",
            ],
            id="token_blacklist_creation",
        ),
    ],
)
def test_auth_model_creation(
    db_session,
    model_factory,
    assertions,
) -> None:
    """Auth models should persist and expose expected values."""
    obj = model_factory(db_session)
    db_session.add(obj)
    db_session.commit()
    for assert_fn in assertions:
        assert_fn(obj)
