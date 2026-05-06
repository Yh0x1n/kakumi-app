"""Behavioral page factory tests for competition UI Slice 1."""

import reflex as rx

from kakumi_app.pages.competition import bracket_page, category_page
from kakumi_app.pages.competition.category_page import _empty_category_state


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


def test_bracket_page_returns_component_with_loading_error_empty_and_data_branches(
) -> None:
    component = bracket_page()
    rendered = _rendered_string(component)

    assert isinstance(component, rx.Component)
    assert "Cargando bracket" in rendered
    assert "No hay encuentros generados aún" in rendered
    assert "Categorías del torneo" in rendered
    assert "/competition/" in rendered


def test_category_page_returns_component_with_safe_placeholder_future_actions() -> None:
    component = category_page()
    rendered = _rendered_string(component)

    assert isinstance(component, rx.Component)
    assert "Cargando categoría" in rendered
    assert "No hay encuentros generados aún" in rendered
    assert "Próxima versión" in rendered
    assert "/scoring/" not in rendered


def test_empty_category_state_shows_name_and_competition_system_context() -> None:
    component = _empty_category_state(
        {
            "id": 7,
            "name": "Kumite Senior",
            "modality": "KUMITE_INDIVIDUAL",
            "competition_system": "ROUND_ROBIN",
            "status": "READY",
        }
    )
    rendered = _rendered_string(component)

    assert isinstance(component, rx.Component)
    assert "Kumite Senior" in rendered
    assert "ROUND_ROBIN" in rendered
    assert "No hay encuentros generados aún" in rendered
