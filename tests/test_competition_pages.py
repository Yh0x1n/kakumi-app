"""Behavioral page factory tests for competition UI Slice 1."""

import importlib
import sys

import reflex as rx

from kakumi_app.pages.competition import bracket_page, category_page, live_match_page
from kakumi_app.pages.competition.category_page import _empty_category_state
from kakumi_app.states.kumite_match_state import KumiteMatchState


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


def test_category_page_returns_component_with_start_match_actions() -> None:
    component = category_page()
    rendered = _rendered_string(component)

    assert isinstance(component, rx.Component)
    assert "Cargando categoría" in rendered
    assert "No hay encuentros generados aún" in rendered
    assert "Iniciar combate" in rendered
    assert "/scoring/" not in rendered


def test_live_match_page_returns_scoreboard_with_real_match_route_contract() -> None:
    component = live_match_page()
    rendered = _rendered_string(component)

    assert isinstance(component, rx.Component)
    assert "Combate en vivo" in rendered
    assert "Exhibition" in rendered
    assert "Establecer 1 min" in rendered
    assert "Establecer 3 min" in rendered
    assert "+10" in rendered
    assert "+1" in rendered
    assert "-1" in rendered
    assert "-10" in rendered
    assert "Otorgar SENSHU" in rendered
    assert "Revocar SENSHU" in rendered


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


def test_exhibition_kumite_route_wires_on_load_exhibition_mode() -> None:
    page_module = importlib.import_module("reflex.page")
    original_count = len(page_module.DECORATED_PAGES.get("kakumi_app", []))

    sys.modules.pop("kakumi_app.pages.exhibition", None)
    importlib.import_module("kakumi_app.pages.exhibition")

    new_pages = page_module.DECORATED_PAGES.get("kakumi_app", [])[original_count:]
    route_configs = [
        config
        for _, config in new_pages
        if config.get("route") == "/exhibition/kumite_system"
    ]
    assert route_configs
    assert route_configs[-1].get("on_load") == KumiteMatchState.enable_exhibition_mode
