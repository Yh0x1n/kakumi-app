"""Category competition operator page for Slice 1."""

from __future__ import annotations

import reflex as rx

from kakumi_app.components.match_card import match_card
from kakumi_app.states.competition_category_state import CompetitionCategoryState
from kakumi_app.utils import CompetitionCategoryData, MatchCardData


def _category_header(category: CompetitionCategoryData) -> rx.Component:
    """Render visible category identity and competition-system context."""
    return rx.vstack(
        rx.heading(category["name"], size="5"),
        rx.text(category["competition_system"]),
        spacing="2",
        align="start",
        width="100%",
    )


def _empty_category_state(category: CompetitionCategoryData) -> rx.Component:
    """Render empty state while preserving category context."""
    return rx.vstack(
        _category_header(category),
        rx.text("No hay encuentros generados aún"),
        spacing="3",
        align="start",
    )


def category_page() -> rx.Component:
    """Render category operator page with loading/error/empty/data branches."""
    state = CompetitionCategoryState
    matches = state.matches.to(list[MatchCardData])

    return rx.container(
        rx.vstack(
            rx.heading("Panel de categoría", size="7"),
            rx.cond(
                state.is_loading,
                rx.text("Cargando categoría"),
                rx.cond(
                    state.error_message,
                    rx.callout(
                        state.error_message,
                        icon="triangle_alert",
                        color_scheme="red",
                    ),
                    rx.cond(
                        matches.length() == 0,
                        rx.cond(
                            state.category,
                            _empty_category_state(state.category),
                            rx.fragment(),
                        ),
                        rx.vstack(
                            rx.cond(
                                state.category,
                                _category_header(state.category),
                            ),
                            rx.foreach(
                                matches,
                                lambda match: match_card(
                                    match,
                                    show_future_action=True,
                                ),
                            ),
                            spacing="4",
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
        max_width="960px",
        padding_y="6",
    )
