"""
User Admin State
Manages CRUD operations for system users (ADMIN/OPERATOR only).
"""

from typing import Any, Optional

import reflex as rx
from sqlmodel import select

from kakumi_app.models.user_model import User
from kakumi_app.services.auth_service import AuthService


class UserAdminState(rx.State):
    """State for user management (RBAC admin page)."""

    # Users list
    users: list[dict[str, Any]] = []
    search_query: str = ""
    error_message: str = ""

    # Form state
    show_form: bool = False
    is_editing: bool = False
    editing_user_id: Optional[int] = None

    # Form fields
    form_username: str = ""
    form_email: str = ""
    form_password: str = ""
    form_full_name: str = ""
    form_role: str = "VIEWER"
    form_is_active: bool = True

    # Confirmation dialog for delete
    show_delete_confirm: bool = False
    deleting_user_id: Optional[int] = None
    deleting_username: str = ""

    @rx.event
    async def load_users(self) -> None:
        """Load all users ordered by username."""
        with rx.session() as session:
            users = session.exec(
                select(User).order_by(User.username)
            ).all()
            self.users = [u.model_dump(mode="json") for u in users]

    @rx.event
    async def filter_users(self) -> None:
        """Filter users by search query (username, email, or full_name)."""
        if not self.search_query:
            await self.load_users()
            return

        q = self.search_query.lower()
        with rx.session() as session:
            all_users = session.exec(
                select(User).order_by(User.username)
            ).all()
            self.users = [
                u.model_dump(mode="json")
                for u in all_users
                if q in u.username.lower()
                or q in u.email.lower()
                or (u.full_name and q in u.full_name.lower())
            ]

    @rx.event
    def set_search_query(self, value: str) -> None:
        """Set search query value."""
        self.search_query = value

    @rx.event
    def open_create_form(self) -> None:
        """Open form in create mode."""
        self.is_editing = False
        self.editing_user_id = None
        self.form_username = ""
        self.form_email = ""
        self.form_password = ""
        self.form_full_name = ""
        self.form_role = "VIEWER"
        self.form_is_active = True
        self.error_message = ""
        self.show_form = True

    @rx.event
    def open_edit_form(self, user: dict[str, Any]) -> None:
        """Open form in edit mode with user data."""
        self.is_editing = True
        self.editing_user_id = user.get("id")
        self.form_username = user.get("username", "")
        self.form_email = user.get("email", "")
        self.form_password = ""  # never prefill password
        self.form_full_name = user.get("full_name", "")
        self.form_role = user.get("role", "VIEWER")
        self.form_is_active = bool(user.get("is_active", True))
        self.error_message = ""
        self.show_form = True

    @rx.event
    def cancel_form(self) -> None:
        """Close form and clear state."""
        self.show_form = False
        self.is_editing = False
        self.editing_user_id = None
        self.error_message = ""

    @rx.event
    def set_form_username(self, value: str) -> None:
        self.form_username = value

    @rx.event
    def set_form_email(self, value: str) -> None:
        self.form_email = value

    @rx.event
    def set_form_password(self, value: str) -> None:
        self.form_password = value

    @rx.event
    def set_form_full_name(self, value: str) -> None:
        self.form_full_name = value

    @rx.event
    def set_form_role(self, value: str) -> None:
        self.form_role = value

    @rx.event
    def set_form_is_active(self, value: bool) -> None:
        self.form_is_active = value

    @rx.event
    async def save_user(self) -> Any:
        """Create or update user."""
        if not self.form_username.strip():
            self.error_message = "Username is required"
            return

        if not self.form_email.strip():
            self.error_message = "Email is required"
            return

        if not self.form_full_name.strip():
            self.error_message = "Full name is required"
            return

        if self.is_editing and self.editing_user_id:
            # Update existing user
            with rx.session() as session:
                user = session.get(User, self.editing_user_id)
                if not user:
                    self.error_message = "User not found"
                    return rx.toast.error("User not found")

                # Check username uniqueness if changed
                if user.username != self.form_username:
                    existing = session.exec(
                        select(User).where(User.username == self.form_username)
                    ).first()
                    if existing:
                        self.error_message = "Username already exists"
                        return

                # Check email uniqueness if changed
                if user.email != self.form_email:
                    existing = session.exec(
                        select(User).where(User.email == self.form_email)
                    ).first()
                    if existing:
                        self.error_message = "Email already exists"
                        return

                user.username = self.form_username.strip()
                user.email = self.form_email.strip()
                user.full_name = self.form_full_name.strip()
                user.role = self.form_role
                user.is_active = self.form_is_active

                # Update password only if provided
                if self.form_password.strip():
                    is_valid, msg = AuthService.validate_password_strength(
                        self.form_password
                    )
                    if not is_valid:
                        self.error_message = f"Weak password: {msg}"
                        return
                    user.password_hash = AuthService.hash_password(self.form_password)
                    user.force_password_change = True

                session.add(user)
                session.commit()

            self.show_form = False
            await self.load_users()
            return rx.toast.success(f"User '{user.username}' updated")
        else:
            # Create new user
            if not self.form_password.strip():
                self.error_message = "Password is required for new users"
                return

            user, error = AuthService.create_user(
                username=self.form_username.strip(),
                email=self.form_email.strip(),
                password=self.form_password,
                full_name=self.form_full_name.strip(),
                role=self.form_role,
                is_active=self.form_is_active,
            )

            if error:
                self.error_message = error
                return

            self.show_form = False
            await self.load_users()
            return rx.toast.success(f"User '{user.username}' created")

    @rx.event
    async def update_user_role(self, user_id: int, role: str) -> Any:
        """Update a user's role directly from table action."""
        with rx.session() as session:
            user = session.get(User, user_id)
            if not user:
                return rx.toast.error("User not found")
            user.role = role
            session.add(user)
            session.commit()

        await self.load_users()
        return rx.toast.success(f"Role updated to {role}")

    @rx.event
    async def toggle_user_active(self, user_id: int) -> Any:
        """Toggle user active/inactive status."""
        with rx.session() as session:
            user = session.get(User, user_id)
            if not user:
                return rx.toast.error("User not found")
            user.is_active = not user.is_active
            session.add(user)
            session.commit()
            new_status = "activated" if user.is_active else "deactivated"

        await self.load_users()
        return rx.toast.success(f"User {new_status}")

    @rx.event
    def confirm_delete(self, user_id: int, username: str) -> None:
        """Show delete confirmation dialog."""
        self.show_delete_confirm = True
        self.deleting_user_id = user_id
        self.deleting_username = username

    @rx.event
    def cancel_delete(self) -> None:
        """Cancel delete confirmation."""
        self.show_delete_confirm = False
        self.deleting_user_id = None
        self.deleting_username = ""

    @rx.event
    async def delete_user(self) -> Any:
        """Delete user (after confirmation)."""
        if not self.deleting_user_id:
            return

        user_id = self.deleting_user_id
        username = self.deleting_username

        with rx.session() as session:
            user = session.get(User, user_id)
            if not user:
                self.show_delete_confirm = False
                return rx.toast.error("User not found")
            session.delete(user)
            session.commit()

        self.show_delete_confirm = False
        self.deleting_user_id = None
        self.deleting_username = ""
        await self.load_users()
        return rx.toast.success(f"User '{username}' deleted")
