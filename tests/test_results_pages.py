"""Behavioral page tests for results routes."""

from __future__ import annotations

import reflex as rx

from kakumi_app.components.sidebar import sidebar_items
from kakumi_app.pages.results import results, tournament_results


def _flatten_render_strings(node: object) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        values: list[str] = []
        for value in node.values():
            values.extend(_flatten_render_strings(value))
        return values
    if isinstance(node, list):
        values: list[str] = []
        for item in node:
            values.extend(_flatten_render_strings(item))
        return values
    return []


def _rendered_string(component: rx.Component) -> str:
    return " ".join(
        value.encode("utf-8").decode("unicode_escape")
        for value in _flatten_render_strings(component.render())
    )


def test_results_index_page_includes_heading_and_empty_state_copy() -> None:
    rendered = _rendered_string(results())

    assert "Resultados" in rendered
    assert "No hay torneos con resultados disponibles todavía" in rendered


def test_tournament_results_page_includes_summary_and_categories_sections() -> None:
    rendered = _rendered_string(tournament_results())

    assert "Resultados del torneo" in rendered
    assert "Resumen" in rendered
    assert "Categorías" in rendered


def test_category_results_page_shows_heading_and_breadcrumb() -> None:
    """Category results page shows heading and breadcrumb back to results."""
    from kakumi_app.pages.results import category_results

    rendered = _rendered_string(category_results())

    assert "Categoría" in rendered
    assert "/results" in rendered


def test_sidebar_items_includes_visible_results_link() -> None:
    rendered = _rendered_string(sidebar_items())

    assert "Resultados" in rendered
    assert "/results" in rendered


def test_podiums_page_shows_heading() -> None:
    """Podiums page renders heading."""
    from kakumi_app.pages.results import podium_results

    rendered = _rendered_string(podium_results())
    assert "Podios" in rendered


def test_statistics_page_shows_heading() -> None:
    """Statistics page renders heading."""
    from kakumi_app.pages.results import statistics

    rendered = _rendered_string(statistics())
    assert "Estadísticas" in rendered
