"""
Authentication Service for Kakumi App

Handles user password hashing, login attempt tracking, lockout, JWT management,
token blacklisting with TTL, refresh rotation and password strength checks.
"""

import bcrypt
import jwt
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

import reflex as rx
from sqlmodel import select

from kakumi_app.models.user_model import User
from kakumi_app.models.login_attempt import LoginAttempt
from kakumi_app.models.token_blacklist import TokenBlacklist
from kakumi_app.models.audit_log import AuditLog

# -- JWT Configuration --
JWT_SECRET_KEY = "supersecretjwt"  # In production, load from env/config!
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 1
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
        """
        Hash a password with bcrypt.
        """
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        return hashed.decode()

    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
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
    ) -> Tuple[Optional[User], str]:
        """Create a new user with password strength validation. Returns (user, error)."""
        # Validate password strength
        is_valid, msg = AuthService.validate_password_strength(password)
        if not is_valid:
            return None, f"Weak password: {msg}"

        # Check if username or email already exists
        with rx.session() as db:
            existing = db.exec(
                select(User).where((User.username == username) | (User.email == email))
            ).first()
            if existing:
                if existing.username == username:
                    return None, "Username already exists"
                return None, "Email already exists"

            # Create user
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
        username: str, ip: str, user_agent: str, success: bool, reason: str = None
    ) -> None:
        """
        Record a login attempt and handle lockout/fail increment.
        Uses session.merge to avoid identity conflict across DB sessions.
        """
        with rx.session() as db:
            user = db.exec(select(User).where(User.username == username)).first()

            # Only update if user exists in this session
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
    def get_user_by_username(username: str) -> Optional[User]:
        """
        Fetch a user by username.
        """
        with rx.session() as db:
            user = db.exec(select(User).where(User.username == username)).first()
            return user

    @staticmethod
    def is_account_locked(user: User) -> Tuple[bool, Optional[datetime]]:
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
        """
        Clear failed_attempts and lockout for a user.
        """
        with rx.session() as db:
            fresh = db.get(User, user.id)
            if fresh:
                fresh.failed_attempts = 0
                fresh.locked_until = None
                db.add(fresh)
                db.commit()

    @staticmethod
    def blacklist_token(token: str, user_id: int, reason: str = "LOGOUT") -> bool:
        """
        Blacklist a JWT (access or refresh).
        Returns True if added, False if already present.
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            jti = payload.get("jti")
            token_type = payload.get("type", "access")
            exp = payload.get("exp")
            expires_at = (
                datetime.utcfromtimestamp(exp)
                if exp
                else (datetime.utcnow() + timedelta(minutes=15))
            )
        except Exception:
            return False
        with rx.session() as db:
            exists = db.exec(
                select(TokenBlacklist).where(TokenBlacklist.token_jti == jti)
            ).first()
            if exists:
                return False
            entry = TokenBlacklist(
                token_jti=jti,
                user_id=user_id,
                token_type=token_type,
                expires_at=expires_at,
                reason=reason,
            )
            db.add(entry)
            db.commit()
            return True

    @staticmethod
    def is_token_blacklisted(token: str) -> bool:
        """
        Check if a token's JTI is blacklisted & not expired.
        """
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": False},
            )
            jti = payload.get("jti")
        except Exception:
            return True  # treat decode error as blacklisted (safer)
        now = datetime.utcnow()
        with rx.session() as db:
            entry = db.exec(
                select(TokenBlacklist)
                .where(TokenBlacklist.token_jti == jti)
                .where(TokenBlacklist.expires_at > now)
            ).first()
            return entry is not None

    @staticmethod
    def refresh_tokens(refresh_token: str) -> Tuple[Optional[str], Optional[str], str]:
        """
        Rotate refresh token: blacklist old, issue new + new access.
        Returns (access_token, refresh_token, error_message)
        """
        try:
            payload = jwt.decode(
                refresh_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM]
            )
            if payload.get("type") != "refresh":
                return None, None, "Not a refresh token"
            user_id = int(payload.get("sub"))
            jti = payload.get("jti")
        except Exception as e:
            return None, None, "Invalid token: " + str(e)
        if AuthService.is_token_blacklisted(refresh_token):
            return None, None, "Token is blacklisted"
        AuthService.blacklist_token(refresh_token, user_id, reason="ROTATED")
        user = None
        with rx.session() as db:
            user = db.get(User, user_id)
        if not user:
            return None, None, "User not found"
        new_access = AuthService._generate_access_token(user)
        new_refresh = AuthService._generate_refresh_token(user)
        return new_access, new_refresh, ""

    @staticmethod
    def _generate_access_token(user: User) -> str:
        """
        Create a new access token for the given user.
        """
        now = datetime.utcnow()
        payload = {
            "sub": str(user.id),
            "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
            "type": "access",
            "jti": AuthService._random_jti(),
            "role": user.role,
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def _generate_refresh_token(user: User) -> str:
        """
        Create a new refresh token for the given user.
        """
        now = datetime.utcnow()
        payload = {
            "sub": str(user.id),
            "exp": now + timedelta(days=REFRESH_TOKEN_DAYS),
            "type": "refresh",
            "jti": AuthService._random_jti(),
            "role": user.role,
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def _random_jti(length: int = 32) -> str:
        """
        Generate a random JWT ID (JTI).
        """
        import random
        import string

        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    @staticmethod
    def login_user(
        username: str, password: str
    ) -> Tuple[Optional[str], Optional[str], str]:
        """Authenticate user and return tokens. Returns (access_token, refresh_token, error)."""
        # Get user by username
        user = AuthService.get_user_by_username(username)
        if not user:
            AuthService.record_login_attempt(
                username, "", "", False, reason="USER_NOT_FOUND"
            )
            return None, None, "Invalid username or password"

        # Check if account is locked
        locked, unlock_at = AuthService.is_account_locked(user)
        if locked:
            AuthService.record_login_attempt(
                username, "", "", False, reason="ACCOUNT_LOCKED"
            )
            return None, None, f"Account is locked. Try again after {unlock_at}"

        # Verify password
        if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            AuthService.record_login_attempt(
                username, "", "", False, reason="INVALID_PASS"
            )
            # Log to audit_log
            with rx.session() as db:
                audit_entry = AuditLog(
                    event_type="LOGIN_FAILED",
                    user_id=user.id,
                    username=username,
                    details="Reason: INVALID_PASS",
                )
                db.add(audit_entry)
                db.commit()
            return None, None, "Invalid username or password"

        # Success - reset failed attempts
        AuthService.record_login_attempt(username, "", "", True, reason="LOGIN_SUCCESS")
        AuthService.reset_failed_attempts(user)

        # Generate tokens
        access_token = AuthService._generate_access_token(user)
        refresh_token = AuthService._generate_refresh_token(user)

        return access_token, refresh_token, ""

    @staticmethod
    def logout_user(token: str) -> bool:
        """Invalidate a token by blacklisting it. Returns True if successful."""
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": False},
            )
            user_id = int(payload.get("sub"))
            success = AuthService.blacklist_token(token, user_id, reason="LOGOUT")
            if success:
                # Log to audit_log
                with rx.session() as db:
                    audit_entry = AuditLog(
                        event_type="LOGOUT",
                        user_id=user_id,
                        details="User logged out",
                    )
                    db.add(audit_entry)
                    db.commit()
            return success
        except Exception:
            return False

    @staticmethod
    def check_permission(user_role: str, required_role: str) -> bool:
        """Check if user_role meets the required_role using hierarchy."""
        user_level = ROLE_HIERARCHY.get(user_role, 0)
        required_level = ROLE_HIERARCHY.get(required_role, 999)
        return user_level >= required_level

    @staticmethod
    def validate_token(token: str) -> Optional[dict]:
        """Validate JWT token and return payload if valid."""
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def get_current_user_from_token(token: str) -> Optional[User]:
        """Get user from JWT token."""
        payload = AuthService.validate_token(token)
        if not payload:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        with rx.session() as db:
            return db.get(User, int(user_id))
