"""
Change Password Page
Forces password change on first login or admin reset.
"""

import reflex as rx

from kakumi_app.states.auth_state import AuthState
from kakumi_app.states.auth_state import DEV_AUTH_BYPASS


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
                "Por seguridad, tu primer inicio de sesión requiere que cambies tu contraseña."
                "Por favor escribe una contraseña robusta",
                font_size="sm",
                margin_bottom="1.5em",
            ),
            rx.form(
                rx.vstack(
                    # Current Password
                    rx.input(
                        placeholder="Contraseña actual",
                        type="password",
                        value=AuthState.cp_current_password,
                        on_change=AuthState.set_cp_current_password,
                        width="100%",
                    ),
                    # New Password
                    rx.input(
                        placeholder="Nueva contraseña",
                        type="password",
                        value=AuthState.cp_new_password,
                        on_change=AuthState.set_cp_new_password,
                        width="100%",
                    ),
                    # Confirm New Password
                    rx.input(
                        placeholder="Confirmar nueva contraseña",
                        type="password",
                        value=AuthState.cp_confirm_password,
                        on_change=AuthState.set_cp_confirm_password,
                        width="100%",
                    ),
                    # Error message
                    rx.cond(
                        AuthState.cp_error,
                        rx.callout(
                            AuthState.cp_error,
                            icon="circle_alert",
                            color_scheme="red",
                            margin_bottom="1em",
                            width="100%",
                        ),
                    ),
                    # Strength hints
                    rx.box(
                        rx.heading("Requisitos de contraseña:", font_size="sm"),
                        rx.vstack(
                            rx.hstack(
                                _strength_icon(AuthState.cp_new_password.length() >= 8),
                                rx.text("Mínimo 8 caracteres", font_size="xs"),
                                spacing="2",
                                align="center",
                            ),
                            rx.hstack(
                                _strength_icon(AuthState.cp_has_uppercase),
                                rx.text("Contiene letra mayúscula", font_size="xs"),
                                spacing="2",
                                align="center",
                            ),
                            rx.hstack(
                                _strength_icon(AuthState.cp_has_lowercase),
                                rx.text("Contiene letra minúscula", font_size="xs"),
                                spacing="2",
                                align="center",
                            ),
                            rx.hstack(
                                _strength_icon(AuthState.cp_has_digit),
                                rx.text("Contiene un número", font_size="xs"),
                                spacing="2",
                                align="center",
                            ),
                            rx.hstack(
                                _strength_icon(AuthState.cp_has_special),
                                rx.text(
                                    "Contiene un carácter especial", font_size="xs"
                                ),
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
                        "Cambiar contraseña",
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
            rx.text("Redireccionando...", font_size="sm"),
        ),
        rx.text("Redireccionando...", font_size="sm"),
    )
