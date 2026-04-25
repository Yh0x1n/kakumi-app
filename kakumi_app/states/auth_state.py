"""
Authentication State
Manages login/logout, token storage, user info, and role-based permissions.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

import reflex as rx

from kakumi_app.services.auth_service import AuthService
from kakumi_app.models.user_model import User


class AuthState(rx.State):
    """State for authentication management."""

    # Token storage (persists across page reloads)
    access_token: str = rx.LocalStorage()
    refresh_token: str = rx.LocalStorage()

    # Current user info (derived from token)
    current_user: Optional[User] = None
    is_authenticated: bool = False
    user_role: str = ""

    # Session timeout tracking
    SESSION_TIMEOUT_MINUTES = 30
    last_activity: str = datetime.utcnow().isoformat()
    session_expired: bool = False

    # Login form fields
    username: str = ""
    password: str = ""

    # UI state
    login_error: str = ""
    is_logging_in: bool = False

    # Initial admin creation flag
    admin_created: bool = False

    def _clear_auth_session(self) -> None:
        """Clear local auth/session data from state."""
        self.access_token = ""
        self.refresh_token = ""
        self.current_user = None
        self.is_authenticated = False
        self.user_role = ""
        self.login_error = ""

    def update_last_activity(self):
        """Update the last activity timestamp."""
        self.last_activity = datetime.utcnow().isoformat()

    @rx.event
    async def check_session_timeout(self):
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
    async def login(self):
        """Authenticate user with username/password."""
        self.is_logging_in = True
        self.login_error = ""

        # Attempt authentication
        access_token, refresh_token, error = AuthService.login_user(
            self.username, self.password
        )

        if error:
            self.login_error = error
            self.is_logging_in = False
            return rx.toast.error(error)

        # Store tokens
        self.access_token = access_token
        self.refresh_token = refresh_token

        # Load user info
        self._load_user_from_token()

        # Update last activity on successful login
        self.update_last_activity()

        # Clear form
        self.username = ""
        self.password = ""
        self.is_logging_in = False

        # Redirect will be handled by frontend (check is_authenticated)
        return [rx.toast.success("Login successful"), rx.redirect("/")]

    @rx.event
    async def logout(self):
        """Log out current user."""
        # Invalidate token on server side (optional)
        if self.access_token:
            AuthService.logout_user(self.access_token)

        # Clear local storage
        self._clear_auth_session()
        self.session_expired = False
        return [rx.toast.info("Logged out"), rx.redirect("/login")]

    def _load_user_from_token(self):
        """Load user information from stored access token."""
        if not self.access_token:
            self.is_authenticated = False
            self.current_user = None
            self.user_role = ""
            return

        # Validate token and get user
        user = AuthService.get_current_user_from_token(self.access_token)
        if user:
            self.current_user = user
            self.is_authenticated = True
            self.user_role = user.role
            # Update last activity on successful token load
            self.update_last_activity()
        else:
            # Token invalid or expired
            self.access_token = ""
            self.refresh_token = ""
            self.is_authenticated = False
            self.current_user = None
            self.user_role = ""

    @rx.event
    async def check_auth(self):
        """Check authentication status (called on page load)."""
        self._load_user_from_token()
        if self.is_authenticated:
            return rx.redirect("/")

    @rx.event
    def set_username(self, value: str):
        self.username = value

    @rx.event
    def set_password(self, value: str):
        self.password = value

    @rx.event
    async def create_initial_admin(self):
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
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@kakumi.com")
        admin_full_name = os.getenv("ADMIN_FULL_NAME", "System Administrator")

        # Create admin user
        user, error = AuthService.create_user(
            username=admin_username,
            email=admin_email,
            password=admin_password,
            full_name=admin_full_name,
            role="ADMIN",
            is_active=True,
        )
        if error:
            # Log error but don't break; user can be created manually
            print(f"Failed to create initial admin: {error}")
        else:
            print(f"Initial admin user '{admin_username}' created.")
            self.admin_created = True

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
