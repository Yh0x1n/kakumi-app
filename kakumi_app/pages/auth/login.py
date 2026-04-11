"""
Login Page
Provides authentication form and handles initial admin creation.
"""

import reflex as rx

from kakumi_app.states.auth_state import AuthState


def login_page() -> rx.Component:
    """Login page component."""
    state = AuthState

    # Ensure initial admin exists when page loads
    state.create_initial_admin()

    # Check if already authenticated
    state.check_auth()

    return rx.cond(
        state.is_authenticated,
        # Already logged in: redirect to home
        rx.redirect("/"),
        # Not authenticated: show login form
        rx.box(
            rx.vstack(
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
                                        on_change=state.set_username,
                                        width="100%",
                                        margin_bottom="1em",
                                    ),
                                    rx.input(
                                        placeholder="Contraseña",
                                        type_="password",
                                        on_change=state.set_password,
                                        width="100%",
                                        margin_bottom="1em",
                                    ),
                                    rx.cond(
                                        state.login_error,
                                        rx.text(
                                            state.login_error,
                                            color="red",
                                            margin_bottom="1em",
                                        ),
                                    ),
                                    rx.button(
                                        "Ingresar",
                                        on_click=state.login,
                                        width="100%",
                                        is_loading=state.is_logging_in,
                                    ),
                                    spacing="4",
                                ),
                                on_submit=lambda e: state.login(),
                            ),
                            rx.text(
                                "Por favor, ingrese sus credenciales.",
                                font_size="0.9em",
                                color="gray",
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
                ),
                spacing="5",
                justify_content="center",
                min_height="100vh",
                background_color="#f5f5f5",
            ),
            width="100%",
            min_height="100vh",
        ),
    )


def login() -> rx.Component:
    """Alias for login_page to match app routing convention."""
    return login_page()
