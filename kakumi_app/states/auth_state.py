"""
Authentication State
Manages login/logout, token storage, user info, and role-based permissions.
"""

import json
import os
import re
from datetime import datetime, timedelta
from typing import Any

import reflex as rx

from kakumi_app.services.auth_service import AuthService
from kakumi_app.models.user_model import User

# Dev auth bypass — NEVER enable in production.
# When active, every session is treated as an authenticated OPERATOR.
DEV_AUTH_BYPASS: bool = os.getenv("DEV_AUTH_BYPASS", "").strip() in (
    "1",
    "true",
    "True",
    "yes",
    "Yes",
)
if DEV_AUTH_BYPASS:
    print("[DEV] DEV_AUTH_BYPASS=1 — auth bypass active, defaulting to OPERATOR role")


class AuthState(rx.State):
    """State for authentication management."""

    # User info persisted as JSON string in browser localStorage
    # (rx.LocalStorage is always str, so we store serialized JSON)
    stored_user_json: str = rx.LocalStorage("")

    # Runtime user info (rehydrated from stored_user_json on page load)
    current_user: dict[str, Any] | None = None
    is_authenticated: bool = False
    user_role: str = ""

    # Session timeout tracking
    SESSION_TIMEOUT_MINUTES = 30
    last_activity: str = datetime.utcnow().isoformat()
    session_expired: bool = False

    # Login form fields
    username: str = ""
    password: str = ""
    show_password: bool = False

    # Password change flow
    needs_password_change: bool = False

    # Change password form fields
    cp_current_password: str = ""
    cp_new_password: str = ""
    cp_confirm_password: str = ""
    cp_error: str = ""

    # UI state
    login_error: str = ""
    is_logging_in: bool = False

    # Initial admin creation flag
    admin_created: bool = False

    def _clear_auth_session(self) -> None:
        """Clear local auth/session data from state."""
        self.stored_user_json = ""
        self.current_user = None
        self.is_authenticated = False
        self.user_role = ""
        self.login_error = ""
        self.needs_password_change = False
        self.cp_error = ""
        self.cp_current_password = ""
        self.cp_new_password = ""
        self.cp_confirm_password = ""

    def refresh_auth(self) -> None:
        """Re-evaluate auth state (idempotent, safe to call from other states)."""
        self._load_user_from_stored()

    def update_last_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = datetime.utcnow().isoformat()

    @rx.event
    async def check_session_timeout(self) -> Any:
        """Expire session on inactivity without returning values."""
        if not self.is_authenticated:
            return
        elapsed = datetime.utcnow() - datetime.fromisoformat(self.last_activity)
        if elapsed > timedelta(minutes=self.SESSION_TIMEOUT_MINUTES):
            self.session_expired = True
            self._clear_auth_session()
            return [
                rx.toast.warning(
                    "Session timed out due to inactivity. Please log in again."
                ),
                rx.redirect("/login"),
            ]

    @rx.event
    async def login(self) -> Any:
        """Authenticate user with username/password."""
        self.is_logging_in = True
        self.login_error = ""

        # Attempt authentication — 3-tuple: (user, force_change, error)
        user, force_change, error = AuthService.login_user(self.username, self.password)

        if error or user is None:
            self.login_error = error
            self.is_logging_in = False
            return rx.toast.error(error)

        # Store user info in state and persist as JSON in localStorage
        user_dict = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
        }
        self.stored_user_json = json.dumps(user_dict)
        self.current_user = user_dict
        self.is_authenticated = True
        self.user_role = user.role

        # Handle force password change
        if force_change:
            self.needs_password_change = True
            self.is_logging_in = False
            return [
                rx.toast.warning("First login: please change your password"),
                rx.redirect("/change-password"),
            ]

        # Update last activity on successful login
        self.update_last_activity()

        # Clear form
        self.username = ""
        self.password = ""
        self.is_logging_in = False

        # Redirect will be handled by frontend (check is_authenticated)
        return [rx.toast.success("Login successful"), rx.redirect("/home")]

    @rx.event
    async def logout(self) -> Any:
        """Log out current user."""
        self._clear_auth_session()
        self.session_expired = False
        return [rx.toast.info("Logged out"), rx.redirect("/login")]

    def _load_user_from_stored(self) -> None:
        """Load user information from stored localStorage JSON."""
        # DEV AUTH BYPASS: skip real auth when env flag is set
        if DEV_AUTH_BYPASS and not self.stored_user_json:
            self.is_authenticated = True
            self.user_role = "OPERATOR"
            self.current_user = {
                "id": 0,
                "username": "dev-bypass",
                "email": "dev@kakumi.local",
                "role": "OPERATOR",
                "is_active": True,
            }
            self.update_last_activity()
            return

        if not self.stored_user_json:
            self.current_user = None
            self.is_authenticated = False
            self.user_role = ""
            return

        try:
            parsed = json.loads(self.stored_user_json)
            if not isinstance(parsed, dict):
                self.current_user = None
                self.is_authenticated = False
                self.user_role = ""
                return
            self.current_user = parsed
            self.is_authenticated = True
            self.user_role = parsed.get("role", "")
        except (json.JSONDecodeError, TypeError):
            self.current_user = None
            self.is_authenticated = False
            self.user_role = ""

    @rx.event
    async def check_auth(self) -> Any:
        """Check authentication status (called on page load)."""
        self._load_user_from_stored()
        # ponytail: removed auto-redirect — login page always shows form
        return None

    @rx.event
    async def check_auth_redirect(self) -> Any:
        """Redirect to /login if not authenticated (called on index on_load)."""
        self._load_user_from_stored()
        if not self.is_authenticated:
            return rx.redirect("/login")

    @rx.event
    def set_username(self, value: str) -> None:
        """Set login username field value."""
        self.username = value

    @rx.event
    def set_password(self, value: str) -> None:
        """Set login password field value."""
        self.password = value

    @rx.event
    def toggle_show_password(self) -> None:
        """Toggle password visibility."""
        self.show_password = not self.show_password

    @rx.event
    async def handle_change_password(self) -> Any:
        """Change user password.

        Validates old password, new password strength, and confirmation match.
        On success, clears force_change flag and redirects to /home.
        """
        self.cp_error = ""

        if self.cp_new_password != self.cp_confirm_password:
            self.cp_error = "Passwords do not match"
            return rx.toast.error("Passwords do not match")

        if not self.is_authenticated or not self.current_user:
            return rx.toast.error("Not authenticated")

        user_id = self.current_user.get("id")
        if not user_id:
            return rx.toast.error("User not found")

        success, error_msg = AuthService.change_password(
            user_id=int(user_id),
            old_password=self.cp_current_password,
            new_password=self.cp_new_password,
        )

        if not success:
            self.cp_error = error_msg
            return rx.toast.error(error_msg)

        self.needs_password_change = False

        self.cp_current_password = ""
        self.cp_new_password = ""
        self.cp_confirm_password = ""

        return [
            rx.toast.success("Password changed successfully"),
            rx.redirect("/home"),
        ]

    @rx.event
    async def set_cp_current_password(self, value: str) -> None:
        """Set change-password current password field."""
        self.cp_current_password = value

    @rx.event
    async def set_cp_new_password(self, value: str) -> None:
        """Set change-password new password field."""
        self.cp_new_password = value

    @rx.event
    async def set_cp_confirm_password(self, value: str) -> None:
        """Set change-password confirm password field."""
        self.cp_confirm_password = value

    @rx.event
    async def check_change_password_access(self) -> Any:
        """Redirect to /login or / if user shouldn't be on this page."""
        if DEV_AUTH_BYPASS:
            return None
        if not self.is_authenticated:
            return [rx.redirect("/login")]
        if not self.needs_password_change:
            return [rx.redirect("/home")]
        return None

    @rx.event
    async def create_initial_admin(self) -> None:
        """
        Create initial admin user if no users exist.
        Uses env vars: ADMIN_USERNAME, ADMIN_PASSWORD,
        ADMIN_EMAIL, ADMIN_FULL_NAME.
        """
        if self.admin_created:
            return

        # Check if any user exists
        with rx.session() as session:
            from sqlmodel import select

            user_count = session.exec(select(User)).all()
            if user_count:
                self.admin_created = True
                return

        # Read from environment
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin1234")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@kakumi.com")
        admin_full_name = os.getenv("ADMIN_FULL_NAME", "System Administrator")

        # Create admin user — bypass password validation since this is a
        # bootstrap password that MUST be changed immediately.
        password_hash = AuthService.hash_password(admin_password)
        user = User(
            username=admin_username,
            email=admin_email,
            password_hash=password_hash,
            full_name=admin_full_name,
            role="ADMIN",
            is_active=True,
            force_password_change=True,
        )
        with rx.session() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
        self.admin_created = True
        print(
            f"Initial admin user '{admin_username}' created. force_password_change=True"
        )

    def _has_permission(self, required_role: str) -> bool:
        """Check if current user has permission for required role."""
        if not self.is_authenticated:
            return False
        return AuthService.check_permission(self.user_role, required_role)

    @rx.var
    def is_admin(self) -> bool:
        """Whether current user has admin-level permissions."""
        return self._has_permission("ADMIN")

    @rx.var
    def is_operator(self) -> bool:
        """Whether current user has operator-level permissions."""
        return self._has_permission("OPERATOR")

    @rx.var
    def cp_has_uppercase(self) -> bool:
        """Whether new password contains at least one uppercase letter."""
        return bool(re.search(r"[A-Z]", self.cp_new_password))

    @rx.var
    def cp_has_lowercase(self) -> bool:
        """Whether new password contains at least one lowercase letter."""
        return bool(re.search(r"[a-z]", self.cp_new_password))

    @rx.var
    def cp_has_digit(self) -> bool:
        """Whether new password contains at least one digit."""
        return bool(re.search(r"[0-9]", self.cp_new_password))

    @rx.var
    def cp_has_special(self) -> bool:
        """Whether new password contains at least one special character."""
        return bool(re.search(r"[^A-Za-z0-9]", self.cp_new_password))
