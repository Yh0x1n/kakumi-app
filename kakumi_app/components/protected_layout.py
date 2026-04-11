"""
Protected Layout Component
Wraps pages with authentication check and sidebar.
"""

import reflex as rx

from kakumi_app.states.auth_state import AuthState
from .sidebar import sidebar


def protected_layout(child: rx.Component) -> rx.Component:
    """
    Returns a layout that requires authentication.
    If not authenticated, redirects to login page.
    """
    auth_state = AuthState

    # Check authentication on mount
    auth_state.check_auth()

    return rx.cond(
        auth_state.is_authenticated,
        # Authenticated: show child with sidebar
        rx.box(
            rx.vstack(
                rx.hstack(
                    sidebar(),
                    rx.box(child, width="100%"),
                    spacing="4",
                ),
            ),
            background_color="white",
            height="100vh",
        ),
        # Not authenticated: redirect to login
        rx.redirect("/login"),
    )
