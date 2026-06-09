"""
Login Page
Provides authentication form and handles initial admin creation.
"""

import reflex as rx

from kakumi_app.states.auth_state import AuthState


@rx.page(route="/login", on_load=[AuthState.create_initial_admin, AuthState.check_auth])
def login_page() -> rx.Component:
    """Login page component."""
    return rx.box(
        rx.center(
            rx.card(
                rx.vstack(
                    rx.heading(
                        "Kakumi Tournament Manager",
                        font_size="2em",
                        font_weight="bold",
                        text_align="center",
                        margin_bottom="0.5em",
                    ),
                    rx.heading(
                        "Iniciar Sesión",
                        font_size="1.5em",
                        font_weight="normal",
                        text_align="center",
                        margin_bottom="1em",
                    ),
                    rx.form(
                        rx.vstack(
                            rx.input(
                                placeholder="Nombre de usuario",
                                on_change=AuthState.set_username,
                                width="100%",
                                margin_bottom="1em",
                            ),
                            rx.input(
                                placeholder="Contraseña",
                                type_="password",
                                on_change=AuthState.set_password,
                                width="100%",
                                margin_bottom="1em",
                            ),
                            rx.cond(
                                AuthState.login_error,
                                rx.text(
                                    AuthState.login_error,
                                    color="red",
                                    margin_bottom="1em",
                                ),
                            ),
                            rx.button(
                                "Ingresar",
                                type="submit",
                                width="100%",
                                is_loading=AuthState.is_logging_in,
                            ),
                            spacing="4",
                        ),
                        on_submit=AuthState.login,
                    ),
                    rx.text(
                        "Por favor, ingrese sus credenciales.",
                        font_size="0.9em",
                        margin_top="1em",
                        text_align="center",
                    ),
                    width="100%",
                    padding="2em",
                ),
                width="400px",
                box_shadow="lg",
                border_radius="lg",
            ),
            min_height="100vh",
        ),
        width="100%",
        min_height="100vh",
    )


def login() -> rx.Component:
    """Alias for login_page to match app routing convention."""
    return login_page()
