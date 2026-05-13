"""Behavioral page factory tests for competition UI Slice 1."""

import importlib
import sys

import reflex as rx

from kakumi_app.pages.competition import (
    bracket_page,
    category_page,
    kata_live_match_page,
    live_match_page,
)
from kakumi_app.components.kata_informal_table import kata_informal_table
from kakumi_app.pages.exhibition import kata_system
from kakumi_app.pages.competition.category_page import _empty_category_state
from kakumi_app.states.kata_match_state import KataMatchState
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


def _flatten_component_names(node: object) -> list[str]:
    if isinstance(node, dict):
        names: list[str] = []
        name = node.get("name")
        if isinstance(name, str):
            names.append(name)
        for value in node.values():
            names.extend(_flatten_component_names(value))
        return names
    if isinstance(node, list):
        names: list[str] = []
        for item in node:
            names.extend(_flatten_component_names(item))
        return names
    return []


def _flatten_cond_states(node: object) -> list[str]:
    if isinstance(node, dict):
        values: list[str] = []
        cond_state = node.get("cond_state")
        if isinstance(cond_state, str):
            values.append(cond_state)
        for value in node.values():
            values.extend(_flatten_cond_states(value))
        return values
    if isinstance(node, list):
        values: list[str] = []
        for item in node:
            values.extend(_flatten_cond_states(item))
        return values
    return []


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
    assert "Iniciar encuentro" in rendered
    assert "/scoring/" not in rendered


def test_live_match_page_returns_scoreboard_with_real_match_route_contract() -> None:
    component = live_match_page()
    component_names = _flatten_component_names(component.render())
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
    assert "Descalificación" in rendered
    assert "SHIKKAKU" in rendered
    assert "KIKEN" in rendered
    assert "Reiniciar puntos" in rendered
    assert "aka_score_color" in rendered
    assert "ao_score_color" in rendered
    assert "HANTEI" in rendered
    assert "Ganó por puntos al finalizar tiempo" not in rendered
    assert "Ganó por SENSHU al finalizar tiempo" not in rendered
    assert "Se requiere HANTEI" not in rendered
    assert "Finalizado por superioridad" not in rendered
    assert "Gana AKA" in rendered
    assert "Gana AO" in rendered
    assert "Entendido" in rendered
    assert "RadixThemesDialog.Root" in component_names
    assert "RadixThemesDialog.Content" in component_names


def test_scoreboard_renders_single_backend_driven_scenario_message_binding() -> None:
    component = live_match_page()
    rendered = _rendered_string(component)

    assert "match_end_message" in rendered
    assert "Ganó por puntos al finalizar tiempo" not in rendered
    assert "Ganó por SENSHU al finalizar tiempo" not in rendered
    assert "Se requiere HANTEI" not in rendered
    assert "Finalizado por superioridad" not in rendered


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


def test_exhibition_kata_route_wires_on_load_exhibition_mode() -> None:
    page_module = importlib.import_module("reflex.page")
    original_count = len(page_module.DECORATED_PAGES.get("kakumi_app", []))

    sys.modules.pop("kakumi_app.pages.exhibition", None)
    importlib.import_module("kakumi_app.pages.exhibition")

    new_pages = page_module.DECORATED_PAGES.get("kakumi_app", [])[original_count:]
    route_configs = [
        config
        for _, config in new_pages
        if config.get("route") == "/exhibition/kata_system"
    ]
    assert route_configs
    assert route_configs[-1].get("on_load") == KataMatchState.enable_exhibition_mode


def test_live_match_routes_register_kata_and_kumite_paths() -> None:
    app_module = importlib.import_module("kakumi_app.kakumi_app")
    routes = {
        f"/{route}" for route in app_module.app._unevaluated_pages.keys()  # noqa: SLF001
    }
    assert "/competition/match/[id]/kata" in routes
    assert "/competition/match/[id]/kumite" in routes


def test_kata_tournament_route_uses_kata_state_and_dedicated_page() -> None:
    app_module = importlib.import_module("kakumi_app.kakumi_app")
    kata_route = app_module.app._unevaluated_pages.get("competition/match/[id]/kata")  # noqa: SLF001

    assert kata_route is not None
    assert kata_route.on_load == KataMatchState.load_match
    assert kata_route.component == kata_live_match_page


def test_category_page_contains_informal_table_header_branch() -> None:
    component = category_page()
    rendered = _rendered_string(component)

    assert "Ranking informal" in rendered
    assert "Puntuar siguiente atleta" in rendered
    assert "Modo torneo" in rendered


def test_exhibition_kata_page_contains_mode_selector() -> None:
    component = kata_system()
    rendered = _rendered_string(component)

    assert "Modo Kata" in rendered
    assert "STANDARD" in rendered
    assert "INFORMAL" in rendered


def test_category_page_informal_mode_shows_single_participant_scoring_panel() -> None:
    component = category_page()
    rendered = _rendered_string(component)

    assert "Puntuar siguiente atleta" in rendered
    assert "Atleta actual" in rendered
    assert "Seleccionar atleta" in rendered
    assert "Guardar puntaje" in rendered


def test_exhibition_kata_informal_mode_shows_single_panel_labels() -> None:
    component = kata_system()
    rendered = _rendered_string(component)

    assert "Atleta actual" in rendered
    assert "Guardar puntaje informal" in rendered
    assert "Ranking informal" in rendered
    assert "Nombre atleta (opcional)" in rendered


def test_category_page_informal_standings_do_not_render_raw_reflex_expr() -> None:
    component = category_page()
    rendered = _rendered_string(component)

    assert '"row_rx_state_?.["rank"]"' not in rendered
    assert '"row_rx_state_?.["athlete_name"]"' not in rendered
    assert '"row_rx_state_?.["final_score"]"' not in rendered
    assert '(isTrue(row_rx_state_?.["rank"]) ? row_rx_state_?.["rank"] : "-")' not in rendered


def test_exhibition_informal_standings_do_not_render_raw_reflex_expr() -> None:
    component = kata_system()
    rendered = _rendered_string(component)

    assert '"row_rx_state_?.["rank"]"' not in rendered
    assert '"row_rx_state_?.["athlete_name"]"' not in rendered
    assert '"row_rx_state_?.["final_score"]"' not in rendered


def test_informal_table_with_concrete_rows_renders_real_rank_name_score() -> None:
    component = kata_informal_table(
        [
            {
                "rank": 1,
                "athlete_name": "Lucía",
                "final_score": "7.800",
                "needs_extra_kata": False,
            }
        ]
    )
    rendered = _rendered_string(component)

    assert "1" in rendered
    assert "Lucía" in rendered
    assert "7.800" in rendered


def test_tournament_page_returns_workspace_shell_with_operator_sections() -> None:
    from kakumi_app.pages.tournament import tournament

    component = tournament()
    rendered = _rendered_string(component)

    assert isinstance(component, rx.Component)
    assert "Workspace del torneo" in rendered
    assert "Seleccioná torneo para gestionar ciclo competitivo" in rendered
    assert "Torneos disponibles" in rendered
    assert "Controles de ciclo" in rendered
    assert "Categorías manuales" in rendered
    assert "Tatamis" in rendered
    assert "Nueva categoría" in rendered


def test_tournament_route_registers_workspace_on_load() -> None:
    app_module = importlib.import_module("kakumi_app.kakumi_app")
    tournament_route = app_module.app._unevaluated_pages.get("tournament")  # noqa: SLF001

    from kakumi_app.pages.tournament import tournament
    from kakumi_app.states.tournament_state import TournamentState

    assert tournament_route is not None
    assert tournament_route.component == tournament
    assert tournament_route.on_load == TournamentState.load_workspace


def test_tournament_page_exposes_full_lifecycle_action_set() -> None:
    from kakumi_app.pages.tournament import tournament

    rendered = _rendered_string(tournament())

    assert "Abrir inscripciones" in rendered
    assert "Cerrar inscripciones" in rendered
    assert "Iniciar competencia" in rendered
    assert "Finalizar torneo" in rendered
    assert "Archivar torneo" in rendered
    assert "Reabrir inscripciones" in rendered
    assert "Cancelar torneo" in rendered


def test_tournament_page_wires_operator_visibility_guards_to_state() -> None:
    from kakumi_app.pages.tournament import tournament

    rendered = tournament().render()
    cond_states = _flatten_cond_states(rendered)
    rendered_text = _rendered_string(tournament())

    assert any("show_lifecycle_controls" in cond for cond in cond_states)
    assert any("show_open_registrations_action" in cond for cond in cond_states)
    assert any("show_cancel_tournament_action" in cond for cond in cond_states)
    assert "Solo operadores autorizados pueden ejecutar transiciones" in rendered_text


def test_tournament_page_exposes_manual_category_crud_fields() -> None:
    from kakumi_app.pages.tournament import tournament

    rendered = _rendered_string(tournament())

    assert "Nueva categoría" in rendered
    assert "Nombre categoría" in rendered
    assert "Edad mínima" in rendered
    assert "Edad máxima" in rendered
    assert "Grado mínimo" in rendered
    assert "Grado máximo" in rendered
    assert "Guardar categoría" in rendered


def test_tournament_page_wires_category_workspace_to_dedicated_state() -> None:
    from kakumi_app.pages.tournament import tournament

    cond_states = _flatten_cond_states(tournament().render())
    rendered = _rendered_string(tournament())

    assert any(
        "has_selected_tournament_context" in cond for cond in cond_states
    )
    assert "Categorías del torneo seleccionado" in rendered
    assert "Eliminar categoría" in rendered


def test_tournament_page_exposes_tatami_crud_and_summary_fields() -> None:
    from kakumi_app.pages.tournament import tournament

    rendered = _rendered_string(tournament())

    assert "Tatamis activos" in rendered
    assert "Nuevo tatami" in rendered
    assert "Nombre tatami" in rendered
    assert "Ubicación / referencia" in rendered
    assert "Guardar tatami" in rendered
    assert "Eliminar tatami" in rendered


def test_tournament_page_wires_tatami_workspace_to_dedicated_state() -> None:
    from kakumi_app.pages.tournament import tournament

    cond_states = _flatten_cond_states(tournament().render())
    rendered = _rendered_string(tournament())

    assert any(
        "has_selected_tournament_context" in cond and "tournament_tatami_state" in cond
        for cond in cond_states
    )
    assert "Tatamis del torneo seleccionado" in rendered
    assert "Tatami rows son fuente de verdad" in rendered
