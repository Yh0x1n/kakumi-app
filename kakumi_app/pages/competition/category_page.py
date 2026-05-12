"""Category competition operator page for Slice 1."""

from __future__ import annotations

import reflex as rx

from kakumi_app.components.kata_informal_table import kata_informal_table
from kakumi_app.components.match_card import match_card
from kakumi_app.states.competition_category_state import CompetitionCategoryState
from kakumi_app.states.kata_informal_state import KataInformalState
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
    standings = state.informal_standings.to(list[dict[str, object]])

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
                        state.is_informal_mode,
                        rx.vstack(
                            rx.cond(
                                state.category,
                                _category_header(state.category),
                                rx.fragment(),
                            ),
                            kata_informal_table(standings),
                             rx.vstack(
                                 rx.heading("Puntuar siguiente atleta", size="4"),
                                rx.text(
                                    rx.cond(
                                        KataInformalState.current_athlete_label != "",
                                        f"Atleta actual: {KataInformalState.current_athlete_label}",
                                        "Atleta actual: —",
                                    )
                                ),
                                rx.hstack(
                                    rx.text("Modo torneo"),
                                    rx.select(
                                        ["STANDARD", "INFORMAL"],
                                        value=state.category["kata_flow_mode"],
                                        on_change=state.set_kata_flow_mode,
                                        width="220px",
                                        size="1",
                                    ),
                                    spacing="2",
                                ),
                                rx.select(
                                    KataInformalState.roster_labels,
                                    on_change=KataInformalState.select_athlete_from_label,
                                    placeholder="Seleccionar atleta",
                                    width="320px",
                                ),
                                rx.hstack(
                                    rx.input(
                                        placeholder="J1",
                                        value=KataInformalState.judge_entries["J1"],
                                        on_change=lambda value: (
                                            KataInformalState.set_judge_score(
                                                "J1",
                                                value,
                                            )
                                        ),
                                        width="80px",
                                    ),
                                    rx.input(
                                        placeholder="J2",
                                        value=KataInformalState.judge_entries["J2"],
                                        on_change=lambda value: (
                                            KataInformalState.set_judge_score(
                                                "J2",
                                                value,
                                            )
                                        ),
                                        width="80px",
                                    ),
                                    rx.input(
                                        placeholder="J3",
                                        value=KataInformalState.judge_entries["J3"],
                                        on_change=lambda value: (
                                            KataInformalState.set_judge_score(
                                                "J3",
                                                value,
                                            )
                                        ),
                                        width="80px",
                                    ),
                                    rx.input(
                                        placeholder="J4",
                                        value=KataInformalState.judge_entries["J4"],
                                        on_change=lambda value: (
                                            KataInformalState.set_judge_score(
                                                "J4",
                                                value,
                                            )
                                        ),
                                        width="80px",
                                    ),
                                    rx.input(
                                        placeholder="J5",
                                        value=KataInformalState.judge_entries["J5"],
                                        on_change=lambda value: (
                                            KataInformalState.set_judge_score(
                                                "J5",
                                                value,
                                            )
                                        ),
                                        width="80px",
                                    ),
                                ),
                                rx.hstack(
                                    rx.button(
                                        "Guardar puntaje",
                                        on_click=KataInformalState.finalize_performance,
                                    ),
                                    rx.button(
                                        "Finalizar categoría",
                                        variant="outline",
                                        on_click=KataInformalState.finalize_category,
                                    ),
                                ),
                                rx.cond(
                                    KataInformalState.error_message != "",
                                    rx.text(
                                        KataInformalState.error_message,
                                        color="red",
                                    ),
                                    rx.fragment(),
                                ),
                                spacing="3",
                                align="start",
                                width="100%",
                            ),
                            spacing="4",
                            width="100%",
                            align="stretch",
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
                                    rx.fragment(),
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
            ),
            spacing="5",
            width="100%",
            align="stretch",
        ),
        max_width="960px",
        padding_y="6",
    )
