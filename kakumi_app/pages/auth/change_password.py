"""
Change Password Page
Forces password change on first login or admin reset.
"""

import reflex as rx

from kakumi_app.states.auth_state import AuthState
from kakumi_app.states.auth_state import DEV_AUTH_BYPASS
from kakumi_app.styles.tokens import BG_PAGE


def _strength_icon(is_valid) -> rx.Component:
    """Show check or X icon for password strength criteria."""
    return rx.icon(
        rx.cond(is_valid, "check", "x"),
        color=rx.cond(is_valid, "green", "red"),
        size=16,
    )


def change_password_form() -> rx.Component:
    """Change password form component."""
    return rx.box(
        rx.vstack(
            rx.heading(
                "Change Password",
                font_size="2xl",
                font_weight="bold",
                margin_bottom="0.5em",
            ),
            rx.text(
                "Your first login requires a password change. "
                "Please choose a new strong password.",
                font_size="sm",
                color="gray",
                margin_bottom="1.5em",
            ),
            rx.form(
                rx.vstack(
                    # Current Password
                    rx.input(
                        placeholder="Current Password",
                        type_="password",
                        value=AuthState.cp_current_password,
                        on_change=AuthState.set_cp_current_password,
                        width="100%",
                    ),
                    # New Password
                    rx.input(
                        placeholder="New Password",
                        type_="password",
                        value=AuthState.cp_new_password,
                        on_change=AuthState.set_cp_new_password,
                        width="100%",
                    ),
                    # Confirm New Password
                    rx.input(
                        placeholder="Confirm New Password",
                        type_="password",
                        value=AuthState.cp_confirm_password,
                        on_change=AuthState.set_cp_confirm_password,
                        width="100%",
                    ),
                    # Error message
                    rx.cond(
                        AuthState.cp_error,
                        rx.callout(
                            AuthState.cp_error,
                            icon="alert-circle",
                            color_scheme="red",
                            margin_bottom="1em",
                            width="100%",
                        ),
                    ),
                    # Strength hints
                    rx.box(
                        rx.heading("Password requirements:", font_size="sm"),
                        rx.vstack(
                            rx.hstack(
                                _strength_icon(
                                    AuthState.cp_new_password.length() >= 8
                                ),
                                rx.text("Minimum 8 characters", font_size="xs"),
                                spacing="2",
                                align="center",
                            ),
                            rx.hstack(
                                _strength_icon(AuthState.cp_has_uppercase),
                                rx.text("Contains uppercase letter", font_size="xs"),
                                spacing="2",
                                align="center",
                            ),
                            rx.hstack(
                                _strength_icon(AuthState.cp_has_lowercase),
                                rx.text("Contains lowercase letter", font_size="xs"),
                                spacing="2",
                                align="center",
                            ),
                            rx.hstack(
                                _strength_icon(AuthState.cp_has_digit),
                                rx.text("Contains a number", font_size="xs"),
                                spacing="2",
                                align="center",
                            ),
                            rx.hstack(
                                _strength_icon(AuthState.cp_has_special),
                                rx.text("Contains a special character",
                                        font_size="xs"),
                                spacing="2",
                                align="center",
                            ),
                            spacing="1",
                            align="start",
                            margin_top="0.5em",
                        ),
                        width="100%",
                        font_size="sm",
                    ),
                    # Submit button
                    rx.button(
                        "Change Password",
                        on_click=AuthState.handle_change_password,
                        width="100%",
                        color_scheme="blue",
                    ),
                    spacing="4",
                ),
                on_submit=AuthState.handle_change_password,
                width="100%",
            ),
            width="100%",
            padding="2em",
        ),
        width="400px",
        box_shadow="lg",
        border_radius="lg",
        bg="white",
    )


@rx.page(route="/change-password", on_load=AuthState.check_change_password_access)
def change_password_page() -> rx.Component:
    """Change password page route.

    Redirects to / if not needs_password_change and not DEV_AUTH_BYPASS.
    Redirects to /login if not authenticated.
    """
    page_content = rx.box(
        rx.vstack(
            rx.center(change_password_form()),
            spacing="5",
            justify_content="center",
            min_height="100vh",
            background_color=BG_PAGE,
        ),
        width="100%",
        min_height="100vh",
    )

    # DEV_AUTH_BYPASS is a plain Python bool — Python-level guard is fine.
    if DEV_AUTH_BYPASS:
        return page_content

    # AuthState vars are Reflex state proxies — must use rx.cond.
    # rx.redirect() returns EventSpec (not Component) in Reflex 0.8.x,
    # so it cannot be used inside rx.cond. Instead, on_load handles redirects.
    return rx.cond(
        AuthState.is_authenticated,
        rx.cond(
            AuthState.needs_password_change,
            page_content,
            rx.text("Redirecting...", font_size="sm"),
        ),
        rx.text("Redirecting...", font_size="sm"),
    )
