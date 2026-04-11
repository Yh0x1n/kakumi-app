"""
Logout Page
Clears authentication and redirects to login.
"""

import reflex as rx

from kakumi_app.states.auth_state import AuthState


def logout_page() -> rx.Component:
    """Logout page component."""
    state = AuthState

    # Perform logout
    state.logout()

    # Redirect to login
    return rx.redirect("/login")


def logout() -> rx.Component:
    """Alias for logout_page."""
    return logout_page()
