"""Results pages for tournament-centric read-only views."""

from __future__ import annotations

import reflex as rx

from kakumi_app.components.registry_crud import registry_page_shell
from kakumi_app.states.results_state import ResultsState


def _results_header(title: str, subtitle: str) -> rx.Component:
    """Render common page heading blocks."""
    return rx.vstack(
        rx.heading(title, size="8"),
        rx.text(subtitle),
        align="start",
        spacing="1",
        width="100%",
    )


def _empty_state(message: str) -> rx.Component:
    """Render a consistent empty-state card."""
    return rx.box(
        rx.text(message, font_weight="medium"),
        width="100%",
        padding="16px",
        border_radius="10px",
        border="1px solid white",
    )


def results() -> rx.Component:
    """Main tournament results index page."""
    body = rx.vstack(
        _results_header(
            "Resultados",
            "Selecciona un torneo para ver su hub de resultados.",
        ),
        rx.cond(
            ResultsState.error_message != "",
            rx.callout(ResultsState.error_message, icon="triangle_alert"),
        ),
        rx.cond(
            ResultsState.is_loading,
            rx.text("Cargando resultados..."),
            rx.cond(
                ResultsState.tournaments,
                rx.vstack(
                    rx.foreach(
                        ResultsState.tournaments,
                        lambda tournament: rx.card(
                            rx.vstack(
                                rx.heading(tournament["name"], size="5"),
                                rx.text(f"Sede: {tournament['venue']}"),
                                rx.text(
                                    f"Categorías: {tournament['category_count']} · "
                                    f"Completadas: {tournament['completed_category_count']}",
                                ),
                                rx.text(
                                    f"Encuentros: {tournament['completed_match_count']}"
                                    f"/{tournament['total_match_count']}",
                                ),
                                rx.link(
                                    "Ver resultados",
                                    href=f"/results/tournament/{tournament['id']}",
                                ),
                                align="start",
                                spacing="2",
                            ),
                            width="100%",
                        ),
                    ),
                    width="100%",
                ),
                _empty_state(
                    "No hay torneos con resultados disponibles todavía",
                ),
            ),
        ),
        width="100%",
        align="start",
        spacing="4",
    )
    return registry_page_shell(body=body)


@rx.page(route="/results/category/[id]", on_load=ResultsState.load_category_view)
def category_results() -> rx.Component:
    """Category drill-down page with matches or kata standings."""

    breadcrumb = rx.hstack(
        rx.link("Resultados", href="/results"),
        rx.text("›"),
        rx.cond(
            ResultsState.category_title != "",
            rx.text(ResultsState.category_title, font_weight="medium"),
            rx.text("Categoría", font_weight="medium"),
        ),
        spacing="2",
        font_size="sm",
        align="center",
    )

    summary_badges = rx.hstack(
        rx.badge(ResultsState.current_category.get("modality", ""), variant="soft"),
        rx.badge(
            ResultsState.current_category.get("competition_system", ""),
            variant="soft",
        ),
        rx.badge(ResultsState.current_category.get("status", ""), variant="outline"),
        rx.badge(ResultsState.current_category.get("gender", ""), variant="soft"),
        wrap="wrap",
        spacing="2",
    )

    heading = rx.cond(
        ResultsState.category_title != "",
        _results_header(
            ResultsState.category_title,
            "Vista detallada de resultados por categoría",
        ),
        _results_header(
            "Categoría",
            "Vista detallada de resultados por categoría",
        ),
    )

    body = rx.vstack(
        breadcrumb,
        heading,
        summary_badges,
        rx.cond(
            ResultsState.error_message != "",
            rx.callout(ResultsState.error_message, icon="triangle_alert"),
        ),
        rx.cond(
            ResultsState.is_loading,
            rx.text("Cargando resultados..."),
            rx.cond(
                ResultsState.empty_message != "",
                _empty_state(ResultsState.empty_message),
                rx.cond(
                    ResultsState.category_standings,
                    rx.vstack(
                        rx.heading("Clasificación", size="5"),
                        rx.foreach(
                            ResultsState.category_standings,
                            lambda entry: rx.card(
                                rx.hstack(
                                    rx.text(
                                        rx.match(
                                            entry.get("rank", 0),
                                            (1, "🥇"),
                                            (2, "🥈"),
                                            (3, "🥉"),
                                            "",
                                        ),
                                        font_size="lg",
                                    ),
                                    rx.text(
                                        entry.get("name", "Atleta"),
                                        font_weight="medium",
                                    ),
                                    rx.spacer(),
                                    rx.badge(
                                        f"{entry.get('total_score', '')} pts",
                                        variant="soft",
                                        color_scheme="green",
                                    ),
                                    rx.badge(
                                        f"{entry.get('victory_points', 0)} VP",
                                        variant="soft",
                                        color_scheme="blue",
                                    ),
                                    spacing="3",
                                    align="center",
                                    width="100%",
                                ),
                                width="100%",
                            ),
                        ),
                        width="100%",
                    ),
                    rx.vstack(
                        rx.heading("Encuentros", size="5"),
                        rx.foreach(
                            ResultsState.category_matches,
                            lambda match: rx.card(
                                rx.hstack(
                                    rx.text(
                                        f"R{match['round']} · E{match['match_number']}",
                                        font_weight="medium",
                                    ),
                                    rx.badge(match["status"], variant="soft"),
                                    spacing="3",
                                    align="center",
                                ),
                                width="100%",
                            ),
                        ),
                        width="100%",
                    ),
                ),
            ),
        ),
        width="100%",
        align="start",
        spacing="4",
    )
    return registry_page_shell(body=body)


@rx.page(route="/results/tournament/[id]", on_load=ResultsState.load_tournament_view)
def tournament_results() -> rx.Component:
    """Tournament results hub page."""
    summary = rx.hstack(
        rx.badge(
            f"Categorías: {ResultsState.tournament_summary.get('total_categories', 0)}"
        ),
        rx.badge(
            f"Completadas: "
            f"{ResultsState.tournament_summary.get('completed_categories', 0)}"
        ),
        rx.badge(
            f"Encuentros: "
            f"{ResultsState.tournament_summary.get('completed_matches', 0)}"
            f"/{ResultsState.tournament_summary.get('total_matches', 0)}"
        ),
        wrap="wrap",
    )

    body = rx.vstack(
        _results_header("Resultados del torneo", "Resumen y categorías"),
        rx.heading("Resumen", size="5"),
        summary,
        rx.cond(
            ResultsState.error_message != "",
            rx.callout(ResultsState.error_message, icon="triangle_alert"),
        ),
        rx.heading("Categorías", size="5"),
        rx.cond(
            ResultsState.is_loading,
            rx.text("Cargando resultados..."),
            rx.cond(
                ResultsState.categories,
                rx.vstack(
                    rx.foreach(
                        ResultsState.categories,
                        lambda category: rx.card(
                            rx.vstack(
                                rx.heading(category["name"], size="4"),
                                rx.text(
                                    f"{category['modality']} · "
                                    f"{category['competition_system']}",
                                ),
                                rx.cond(
                                    category.get("podium_status") == "available",
                                    rx.vstack(
                                        rx.text(
                                            f"🥇 {category.get('first_place_name', '—')}",
                                            font_weight="bold",
                                        ),
                                        rx.text(
                                            f"🥈 {category.get('second_place_name', '—')}",
                                        ),
                                        rx.cond(
                                            category.get("third_place_display", ""),
                                            rx.text(
                                                f"🥉 {category.get('third_place_display', '')}",
                                            ),
                                        ),
                                        spacing="1",
                                        width="100%",
                                        align="start",
                                    ),
                                    rx.cond(
                                        category.get("is_informal", False),
                                        rx.text(
                                            f"Estado: {category.get('podium_status', '—')}",
                                        ),
                                        rx.text(
                                            f"Progreso: {category['completed_match_count']}"
                                            f"/{category['total_match_count']}",
                                        ),
                                    ),
                                ),
                                rx.badge(
                                    f"Podio: {category['podium_status']}",
                                    color_scheme="gray",
                                ),
                                width="100%",
                                align="start",
                                spacing="2",
                            ),
                            width="100%",
                        ),
                    ),
                    width="100%",
                ),
                _empty_state("No hay resultados disponibles todavía"),
            ),
        ),
        width="100%",
        align="start",
        spacing="4",
    )
    return registry_page_shell(body=body)


def _podium_status_badge(status: str) -> rx.Component:
    """Render a badge for podium status."""
    color_scheme = rx.match(
        status,
        ("available", "green"),
        ("incomplete", "orange"),
        ("unsupported_team", "gray"),
        ("not_completed", "blue"),
        "gray",
    )
    label = rx.match(
        status,
        ("available", "Podio disponible"),
        ("incomplete", "Podio incompleto"),
        ("unsupported_team", "Equipo — no soportado aún"),
        ("not_completed", "Categoría no finalizada"),
        status,
    )
    return rx.badge(label, color_scheme=color_scheme, variant="soft")


@rx.page(route="/results/podiums", on_load=ResultsState.load_podiums_view)
def podium_results() -> rx.Component:
    """Podium card view with status badges."""
    body = rx.vstack(
        _results_header(
            "Podios",
            "Vista de podios por torneo.",
        ),
        rx.cond(
            ResultsState.error_message != "",
            rx.callout(ResultsState.error_message, icon="triangle_alert"),
        ),
        rx.cond(
            ResultsState.is_loading,
            rx.text("Cargando podios..."),
            rx.cond(
                ResultsState.podium_cards,
                rx.vstack(
                    rx.foreach(
                        ResultsState.podium_cards,
                        lambda card: rx.card(
                            rx.vstack(
                                rx.heading(card["name"], size="4"),
                                _podium_status_badge(card["podium_status"]),
                                rx.cond(
                                    card["podium_status"] == "available",
                                    rx.vstack(
                                        rx.text(
                                            f"🥇 {card['first_place_name']}",
                                            font_weight="bold",
                                        ),
                                        rx.text(
                                            f"🥈 {card['second_place_name']}",
                                        ),
                                        rx.cond(
                                            card["third_place_display"],
                                            rx.text(
                                                f"🥉 {card['third_place_display']}",
                                            ),
                                        ),
                                        spacing="1",
                                    ),
                                ),
                                rx.text(
                                    f"{card.get('modality', '')} · "
                                    f"{card.get('competition_system', '')}",
                                    font_size="sm",
                                ),
                                align="start",
                                spacing="2",
                            ),
                            width="100%",
                        ),
                    ),
                    width="100%",
                ),
                _empty_state("No hay podios disponibles para este torneo."),
            ),
        ),
        width="100%",
        align="start",
        spacing="4",
    )
    return registry_page_shell(body=body)


@rx.page(route="/results/statistics", on_load=ResultsState.load_statistics_view)
def statistics() -> rx.Component:
    """Statistics view with summary badges and breakdown tables."""
    summary = rx.hstack(
        rx.badge(
            f"Categorías totales: "
            f"{ResultsState.statistics_view.get('total_categories', 0)}"
        ),
        rx.badge(
            f"Completadas: "
            f"{ResultsState.statistics_view.get('completed_categories', 0)}"
        ),
        rx.badge(
            f"Encuentros totales: "
            f"{ResultsState.statistics_view.get('total_matches', 0)}"
        ),
        rx.badge(
            f"Completados: {ResultsState.statistics_view.get('completed_matches', 0)}"
        ),
        wrap="wrap",
        spacing="2",
    )

    body = rx.vstack(
        _results_header(
            "Estadísticas",
            "Métricas de resultados del torneo.",
        ),
        rx.cond(
            ResultsState.error_message != "",
            rx.callout(ResultsState.error_message, icon="triangle_alert"),
        ),
        rx.cond(
            ResultsState.is_loading,
            rx.text("Cargando estadísticas..."),
            rx.cond(
                ResultsState.statistics_view,
                rx.vstack(
                    rx.heading("Resumen", size="5"),
                    summary,
                    rx.cond(
                        ResultsState.modality_breakdown,
                        rx.vstack(
                            rx.heading("Por modalidad", size="5"),
                            rx.foreach(
                                ResultsState.modality_breakdown,
                                lambda row: rx.card(
                                    rx.hstack(
                                        rx.text(row["modality"], font_weight="medium"),
                                        rx.text(
                                            f"{row['completed_categories']}"
                                            f"/{row['total_categories']} categorías"
                                        ),
                                        spacing="3",
                                        align="center",
                                    ),
                                    width="100%",
                                ),
                            ),
                            width="100%",
                        ),
                    ),
                    rx.cond(
                        ResultsState.system_breakdown,
                        rx.vstack(
                            rx.heading("Por sistema", size="5"),
                            rx.foreach(
                                ResultsState.system_breakdown,
                                lambda row: rx.card(
                                    rx.hstack(
                                        rx.text(row["system"], font_weight="medium"),
                                        rx.text(
                                            f"{row['total_categories']} categorías"
                                        ),
                                        spacing="3",
                                        align="center",
                                    ),
                                    width="100%",
                                ),
                            ),
                            width="100%",
                        ),
                    ),
                    rx.cond(
                        ResultsState.match_status_breakdown,
                        rx.vstack(
                            rx.heading("Por estado de encuentro", size="5"),
                            rx.foreach(
                                ResultsState.match_status_breakdown,
                                lambda row: rx.card(
                                    rx.hstack(
                                        rx.text(row["status"], font_weight="medium"),
                                        rx.text(f"{row['count']} encuentros"),
                                        spacing="3",
                                        align="center",
                                    ),
                                    width="100%",
                                ),
                            ),
                            width="100%",
                        ),
                    ),
                    width="100%",
                    spacing="4",
                ),
                _empty_state("No hay estadísticas disponibles para este torneo."),
            ),
        ),
        width="100%",
        align="start",
        spacing="4",
    )
    return registry_page_shell(body=body)
