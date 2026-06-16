"""
Authentication Service for Kakumi App

Handles user password hashing, login attempt tracking, lockout,
password strength checks, and role-based authorization.
"""

import re
from datetime import datetime, timedelta

import bcrypt
import reflex as rx
from sqlmodel import select

from kakumi_app.models.audit_log import AuditLog
from kakumi_app.models.login_attempt import LoginAttempt
from kakumi_app.models.user_model import User

LOCKOUT_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)

# Role hierarchy for RBAC
ROLE_HIERARCHY = {
    "ADMIN": 3,
    "OPERATOR": 2,
    "VIEWER": 1,
}


class AuthService:
    """Auth-related utilities and flows."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password with bcrypt."""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """
        Check PW: min 8chars, uppercase, number, special char.
        Returns (is_valid, message).
        """
        if len(password) < 8:
            return False, "Password must contain min 8 characters."
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain uppercase."
        if not re.search(r"[a-z]", password):
            return False, "Password must contain min lowercase."
        if not re.search(r"[0-9]", password):
            return False, "Password must contain number."
        if not re.search(r"[^A-Za-z0-9]", password):
            return False, "Password must contain special."
        return True, "Password is strong."

    @staticmethod
    def create_user(
        username: str,
        email: str,
        password: str,
        full_name: str,
        role: str = "OPERATOR",
        is_active: bool = True,
    ) -> tuple[User | None, str]:
        """Create user with password validation.

        Returns a tuple: (user, error_message).
        """
        is_valid, msg = AuthService.validate_password_strength(password)
        if not is_valid:
            return None, f"Weak password: {msg}"

        with rx.session() as db:
            existing = db.exec(
                select(User).where((User.username == username) | (User.email == email))
            ).first()
            if existing:
                if existing.username == username:
                    return None, "Username already exists"
                return None, "Email already exists"

            user = User(
                username=username,
                email=email,
                password_hash=AuthService.hash_password(password),
                full_name=full_name,
                role=role,
                is_active=is_active,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user, ""

    @staticmethod
    def record_login_attempt(
        username: str,
        ip: str,
        user_agent: str,
        success: bool,
        reason: str | None = None,
    ) -> None:
        """
        Record a login attempt and handle lockout/fail increment.
        Uses session.merge to avoid identity conflict across DB sessions.
        """
        with rx.session() as db:
            user = db.exec(select(User).where(User.username == username)).first()

            if user is not None:
                if not success:
                    user.failed_attempts += 1
                    if user.failed_attempts >= LOCKOUT_ATTEMPTS:
                        user.locked_until = datetime.utcnow() + LOCKOUT_DURATION
                else:
                    user.failed_attempts = 0
                    user.locked_until = None
                db.merge(user)
                db.commit()

            attempt = LoginAttempt(
                username=username,
                ip_address=ip,
                user_agent=user_agent,
                was_successful=success,
                failure_reason=reason,
            )
            db.add(attempt)
            db.commit()

    @staticmethod
    def get_user_by_username(username: str) -> User | None:
        """Fetch a user by username."""
        with rx.session() as db:
            return db.exec(select(User).where(User.username == username)).first()

    @staticmethod
    def is_account_locked(user: User) -> tuple[bool, datetime | None]:
        """
        Check lockout status. Unlock if expired, persist.
        Returns (is_locked, unlock_time or None)
        """
        if not user.locked_until:
            return False, None
        if datetime.utcnow() < user.locked_until:
            return True, user.locked_until
        # Unlock if expired
        with rx.session() as db:
            fresh = db.get(User, user.id)
            if fresh:
                fresh.locked_until = None
                fresh.failed_attempts = 0
                db.add(fresh)
                db.commit()
        return False, None

    @staticmethod
    def reset_failed_attempts(user: User) -> None:
        """Clear failed_attempts and lockout for a user."""
        with rx.session() as db:
            fresh = db.get(User, user.id)
            if fresh:
                fresh.failed_attempts = 0
                fresh.locked_until = None
                db.add(fresh)
                db.commit()

    @staticmethod
    def login_user(username: str, password: str) -> tuple[User | None, bool, str]:
        """Authenticate user and return user info.

        Returns: (user, force_password_change, error_message).
        force_password_change is True when the user must change their password.
        On error, user is None and error_message describes the issue.
        """
        user = AuthService.get_user_by_username(username)
        if not user:
            AuthService.record_login_attempt(
                username, "", "", False, reason="USER_NOT_FOUND"
            )
            return None, False, "Invalid username or password"

        locked, unlock_at = AuthService.is_account_locked(user)
        if locked:
            AuthService.record_login_attempt(
                username, "", "", False, reason="ACCOUNT_LOCKED"
            )
            return None, False, f"Account is locked. Try again after {unlock_at}"

        if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            AuthService.record_login_attempt(
                username, "", "", False, reason="INVALID_PASS"
            )
            with rx.session() as db:
                audit_entry = AuditLog(
                    event_type="LOGIN_FAILED",
                    user_id=user.id,
                    username=username,
                    details="Reason: INVALID_PASS",
                )
                db.add(audit_entry)
                db.commit()
            return None, False, "Invalid username or password"

        # Success
        AuthService.record_login_attempt(username, "", "", True, reason="LOGIN_SUCCESS")
        AuthService.reset_failed_attempts(user)

        # Re-fetch user to get fresh force_password_change flag
        with rx.session() as db:
            fresh_user = db.get(User, user.id)
            force_change = fresh_user.force_password_change if fresh_user else False

        return user, force_change, ""

    @staticmethod
    def change_password(
        user_id: int, old_password: str, new_password: str
    ) -> tuple[bool, str]:
        """Change user password.

        Validates old password, strength-checks new password, updates hash,
        and clears force_password_change flag.

        Returns: (success, error_message). On success error_message is empty.
        """
        with rx.session() as db:
            user = db.get(User, user_id)
            if not user:
                return False, "User not found"

            if not bcrypt.checkpw(old_password.encode(), user.password_hash.encode()):
                return False, "Current password is incorrect"

            is_valid, msg = AuthService.validate_password_strength(new_password)
            if not is_valid:
                return False, msg

            user.password_hash = AuthService.hash_password(new_password)
            user.force_password_change = False
            db.add(user)
            db.commit()

        return True, ""

    @staticmethod
    def check_permission(user_role: str, required_role: str) -> bool:
        """Check if user_role meets or exceeds required_role in RBAC hierarchy.

        Role order (highest to lowest): ADMIN (3) > OPERATOR (2) > VIEWER (1).
        Unknown roles default to 0 (no access). Unknown required_role defaults to
        999 (deny all).

        This is the SINGLE source of truth for role checks in Kakumi.
        All States must delegate to this method — do NOT duplicate ROLE_HIERARCHY.

        Args:
            user_role: Current user's role string.
            required_role: Minimum role string required for action.

        Returns:
            True if user_role level >= required_role level.
        """
        user_level = ROLE_HIERARCHY.get(user_role, 0)
        required_level = ROLE_HIERARCHY.get(required_role, 999)
        return user_level >= required_level
