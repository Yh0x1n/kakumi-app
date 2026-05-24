"""
Protected Layout Component
Wraps pages with authentication check and sidebar.
"""

import reflex as rx

from kakumi_app.states.auth_state import AuthState
from .sidebar import sidebar
from kakumi_app.styles.tokens import TEXT_TERTIARY, BG_PAGE


def protected_layout(
    child: rx.Component, required_role: str = "VIEWER"
) -> rx.Component:
    """
    Returns a layout that requires authentication and role-based access.

    If not authenticated, redirects to login page.
    If authenticated but lacks required role, shows denied message.

    Args:
        child: The page content component.
        required_role: Minimum role required (VIEWER, OPERATOR, ADMIN).
                       Defaults to VIEWER for backward compatibility.
    """
    auth_state = AuthState

    # Check authentication on mount
    auth_state.check_auth()

    return rx.cond(
        auth_state.is_authenticated,
        rx.cond(
            auth_state._has_permission(required_role),
            # Has permission: show child with sidebar
            rx.box(
                rx.vstack(
                    rx.hstack(
                        sidebar(),
                        rx.box(child, width="100%"),
                        spacing="4",
                    ),
                ),
                background_color=BG_PAGE,
                height="100vh",
            ),
            # Denied: show permission error
            rx.box(
                rx.vstack(
                    rx.heading(
                        "Access Denied",
                        font_size="3xl",
                        font_weight="bold",
                        color="red",
                    ),
                    rx.text(
                        "You don't have permission to access this page.",
                        font_size="lg",
                        color=TEXT_TERTIARY,
                    ),
                    rx.button(
                        "Go Home",
                        on_click=rx.redirect("/"),
                        color_scheme="blue",
                        margin_top="1em",
                    ),
                    spacing="4",
                    justify_content="center",
                    align_items="center",
                    min_height="50vh",
                ),
                width="100%",
                padding="2em",
                on_mount=rx.toast.error("Access denied"),
            ),
        ),
        # Not authenticated: redirect to login
        rx.redirect("/login"),
    )
