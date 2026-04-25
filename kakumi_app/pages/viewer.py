"""
Viewer Pages
Login page for viewer code entry and dashboard for live results.
"""

import reflex as rx

from kakumi_app.states.viewer_state import ViewerState
from kakumi_app.styles.tokens import BG_CARD_ALT, BG_PAGE

# NOTE: Bracket components not yet implemented
# from kakumi_app.components.bracket_view import bracket_view
# from kakumi_app.states.bracket_state import BracketState


def viewer_login_page() -> rx.Component:
    """Viewer login page component."""
    state = ViewerState

    return rx.box(
        rx.vstack(
            rx.center(
                rx.card(
                    rx.vstack(
                        rx.heading(
                            "Kakumi - Acceso Espectadores",
                            font_size="2em",
                            font_weight="bold",
                            text_align="center",
                            margin_bottom="0.5em",
                        ),
                        rx.heading(
                            "Ingrese código de torneo",
                            font_size="1.5em",
                            font_weight="normal",
                            text_align="center",
                            margin_bottom="1em",
                        ),
                        rx.form(
                            rx.vstack(
                                rx.input(
                                    placeholder="Código de espectador (8 caracteres)",
                                    on_change=state.set_viewer_code,
                                    width="100%",
                                    margin_bottom="1em",
                                    max_length=8,
                                ),
                                rx.button(
                                    "Acceder",
                                    on_click=state.validate_and_load_tournament,
                                    width="100%",
                                    is_loading=state.is_loading,
                                ),
                                spacing="4",
                            ),
                            on_submit=lambda e: state.validate_and_load_tournament(),
                        ),
                        rx.text(
                            (
                                "El código le permitirá ver los resultados "
                                "en vivo del torneo."
                            ),
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
            background_color=BG_PAGE,
        ),
        width="100%",
        min_height="100vh",
    )


def viewer_login() -> rx.Component:
    """Alias for viewer_login_page."""
    return viewer_login_page()


def viewer_dashboard_page(tournament_id: int) -> rx.Component:
    """Viewer dashboard page showing tournament live results."""
    state = ViewerState

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.heading(
                    f"Torneo: {state.current_tournament.name}",
                    font_size="2em",
                    font_weight="bold",
                    color="black",
                ),
                rx.spacer(),
                rx.button(
                    "Cerrar sesión",
                    on_click=state.clear_viewer_session,
                    color_scheme="red",
                ),
                padding="1em",
                background_color="white",
                width="100%",
            ),
            rx.box(
                rx.vstack(
                    rx.heading("Información del Torneo", size="4"),
                    rx.text(f"Fecha: {state.current_tournament.date}"),
                    rx.text(f"Estado: {state.current_tournament.status}"),
                    rx.text(f"Código de espectador: {state.viewer_code}"),
                    padding="1em",
                    background_color=BG_CARD_ALT,
                    border_radius="0.5em",
                    margin_bottom="1em",
                ),
                width="100%",
                padding="0 1em",
            ),
            rx.box(
                rx.vstack(
                    rx.heading("Categorías", size="4"),
                    rx.cond(
                        state.categories.length == 0,
                        rx.text("No hay categorías disponibles."),
                        rx.foreach(
                            state.categories,
                            lambda cat: rx.button(
                                f"{cat['name']} ({cat['type']})",
                                on_click=lambda: state.select_category(
                                    cat["id"], cat["type"]
                                ),
                                margin_bottom="0.5em",
                                width="100%",
                            ),
                        ),
                    ),
                    padding="1em",
                    background_color="white",
                    border_radius="0.5em",
                    margin_bottom="1em",
                ),
                width="100%",
                padding="0 1em",
            ),
            rx.box(
                rx.vstack(
                    rx.heading("Bracket en Vivo", size="4"),
                    rx.text(
                        (
                            "La visualización de brackets estará disponible "
                            "cuando se implementen los modelos de partidos."
                        ),
                        color="gray",
                    ),
                    padding="1em",
                    background_color="white",
                    border_radius="0.5em",
                    margin_bottom="1em",
                ),
                width="100%",
                padding="0 1em",
            ),
            spacing="4",
            background_color=BG_PAGE,
            min_height="100vh",
        ),
        width="100%",
    )
