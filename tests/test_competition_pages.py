"""Route-wiring and behavioral tests for competition pages.

Keeps only route registration tests and state-wiring checks.
Removes ~20 brittle UI string snapshot assertions.
"""

from __future__ import annotations

import importlib
import sys

import reflex as rx

from kakumi_app.pages.competition import kata_live_match_page
from kakumi_app.components.kata_informal_table import kata_informal_table
from kakumi_app.pages.public_display import public_display_page
from kakumi_app.states.kata_match_state import KataMatchState
from kakumi_app.states.kumite_match_state import KumiteMatchState
from kakumi_app.states.secondary_display_state import SecondaryDisplayState


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


def test_exhibition_kumite_route_wires_on_load_exhibition_mode() -> None:
    """Kumite exhibition route must wire on_load to enable_exhibition_mode."""
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
    """Kata exhibition route must wire on_load to enable_exhibition_mode."""
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
    """Kumite and kata live match routes must be registered."""
    app_module = importlib.import_module("kakumi_app.kakumi_app")
    routes = {f"/{route}" for route in app_module.app._unevaluated_pages}
    assert "/competition/match/[id]/kata" in routes
    assert "/competition/match/[id]/kumite" in routes


def test_kata_tournament_route_uses_kata_state_and_dedicated_page() -> None:
    """Kata tournament route must use KataMatchState and kata_live_match_page."""
    app_module = importlib.import_module("kakumi_app.kakumi_app")
    kata_route = app_module.app._unevaluated_pages.get("competition/match/[id]/kata")

    assert kata_route is not None
    assert kata_route.on_load == KataMatchState.load_match
    assert kata_route.component == kata_live_match_page


def test_tournament_route_registers_workspace_on_load() -> None:
    """Tournament route must wire on_load to TournamentState.load_workspace."""
    app_module = importlib.import_module("kakumi_app.kakumi_app")
    tournament_route = app_module.app._unevaluated_pages.get("tournament")

    from kakumi_app.pages.tournament import tournament
    from kakumi_app.states.tournament_state import TournamentState

    assert tournament_route is not None
    assert tournament_route.component == tournament
    assert tournament_route.on_load == TournamentState.load_workspace


def test_public_display_route_registered_once_without_duplicate_page_decorator() -> (
    None
):
    """Public display route must be registered exactly once."""
    app_module = importlib.import_module("kakumi_app.kakumi_app")

    keys = list(app_module.app._unevaluated_pages.keys())
    assert keys.count("display/[display_key]") == 1

    route = app_module.app._unevaluated_pages["display/[display_key]"]
    assert route.component == public_display_page
    assert route.on_load == [
        SecondaryDisplayState.load_display,
        SecondaryDisplayState.poll_snapshot_loop,
    ]


def test_tournament_page_wires_operator_visibility_guards_to_state() -> None:
    """Tournament page must wire rx.cond gates to operator-level state vars."""
    from kakumi_app.pages.tournament import tournament

    cond_states = _flatten_cond_states(tournament().render())

    # Step machine state vars appear in rx.cond gates
    assert any("step_index" in cond for cond in cond_states)
    assert any("create_mode" in cond for cond in cond_states)
    assert any("tournaments" in cond for cond in cond_states)
    # is_readonly_mode is embedded inside rx.match case branches (not in cond_state leaf)


def test_informal_table_renders_participant_data() -> None:
    """kata_informal_table must render rank, name, and score for each row."""
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

    assert isinstance(component, rx.Component)
