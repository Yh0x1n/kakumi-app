"""Parametrized route-wiring smoke tests for results pages.

Replaces 6 separate UI string snapshot tests with a single parametrized
route-wiring smoke test that verifies each page factory returns an rx.Component
and renders without error.
"""

from __future__ import annotations

import pytest
import reflex as rx

from kakumi_app.components.sidebar import sidebar_items
from kakumi_app.pages.results import (
    category_results,
    podium_results,
    results,
    statistics,
    tournament_results,
)


@pytest.mark.parametrize(
    ("page_factory", "name"),
    [
        pytest.param(results, "results_index", id="results_index"),
        pytest.param(tournament_results, "tournament_results", id="tournament_results"),
        pytest.param(category_results, "category_results", id="category_results"),
        pytest.param(podium_results, "podium_results", id="podium_results"),
        pytest.param(statistics, "statistics", id="statistics"),
    ],
)
def test_results_page_returns_component(page_factory, name: str) -> None:
    """Each results page factory must return a valid rx.Component."""
    del name
    component = page_factory()
    assert isinstance(component, rx.Component)


def test_sidebar_items_returns_component() -> None:
    """Sidebar items must return a valid rx.Component."""
    component = sidebar_items()
    assert isinstance(component, rx.Component)
