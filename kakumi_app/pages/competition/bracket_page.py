"""Tournament bracket page for operator read-heavy view."""

from __future__ import annotations

import reflex as rx

from kakumi_app.components.bracket_round import bracket_round
from kakumi_app.states.bracket_state import BracketState
from kakumi_app.utils import BracketCategoryData, BracketRoundData


def _category_section(category: BracketCategoryData) -> rx.Component:
    """Render one category bracket section."""
    rounds = category["rounds"].to(list[BracketRoundData])
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.heading(category["name"], size="5"),
                    rx.text(category["competition_system"]),
                    spacing="2",
                    align="start",
                ),
                rx.spacer(),
                rx.link(
                    rx.button("Abrir categoría"),
                    href=f"/competition/category/{category['id']}",
                ),
                width="100%",
                align="center",
            ),
            rx.cond(
                rounds.length() == 0,
                rx.text("No hay encuentros generados aún"),
                rx.hstack(
                    rx.foreach(rounds, bracket_round),
                    spacing="6",
                    width="100%",
                    align="start",
                    overflow_x="auto",
                ),
            ),
            spacing="4",
            width="100%",
            align="stretch",
        ),
        width="100%",
    )


def bracket_page() -> rx.Component:
    """Render tournament bracket page with loading/error/empty/data branches."""
    state = BracketState
    categories = state.categories.to(list[BracketCategoryData])

    return rx.container(
        rx.vstack(
            rx.heading("Categorías del torneo", size="7"),
            rx.cond(
                state.is_loading,
                rx.text("Cargando bracket"),
                rx.cond(
                    state.error_message,
                    rx.callout(
                        state.error_message,
                        icon="triangle_alert",
                        color_scheme="red",
                    ),
                    rx.cond(
                        categories.length() == 0,
                        rx.text("No hay encuentros generados aún"),
                        rx.vstack(
                            rx.cond(
                                state.tournament,
                                rx.vstack(
                                    rx.heading(state.tournament["name"], size="5"),
                                    rx.text(state.tournament["status"]),
                                    spacing="2",
                                    align="start",
                                    width="100%",
                                ),
                            ),
                            rx.foreach(categories, _category_section),
                            spacing="5",
                            width="100%",
                            align="stretch",
                        ),
                    ),
                ),
            ),
            spacing="5",
            width="100%",
            align="stretch",
        ),
        max_width="1400px",
        padding_y="6",
    )
