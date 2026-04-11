"""
Tests for password strength validation.
"""

import pytest
from kakumi_app.services.auth_service import AuthService


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
    """Test password strength validation with various inputs."""
    is_valid, _ = AuthService.validate_password_strength(password)
    assert is_valid == should_pass
