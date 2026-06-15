"""Parametrized regression tests for admin registry alias wrappers.

Collapses duplicate base+new route tests into parametrized form.
Keeps unique tests for reg_item, thin wrappers, and tournaments route.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import get_args

import pytest
import reflex as rx

from kakumi_app.components.registries_items import reg_item

ROOT = Path(__file__).resolve().parents[1]


def _route_config(route: str) -> dict:
    """Return Reflex page config for given route."""
    page_module = importlib.import_module("reflex.page")
    pages = page_module.DECORATED_PAGES.get("kakumi_app", [])
    for _, config in reversed(pages):
        if config.get("route") == route:
            return config
    msg = f"route not registered: {route}"
    raise AssertionError(msg)


def _redirect_path(event_spec: rx.event.EventSpec) -> str:
    """Extract redirect target path from Reflex event spec."""
    path_var = event_spec.args[0][1]
    return path_var._var_value


def test_reg_item_icon_type_allows_component_and_string() -> None:
    """reg_item accepts icon path strings and Reflex components."""
    icon_annotation = reg_item.__annotations__["icon"]
    icon_types = get_args(icon_annotation)

    assert str in icon_types
    assert rx.Component in icon_types


def test_admin_athletes_referee_pages_are_thin_wrappers() -> None:
    """Legacy admin pages stay as thin aliases over shared registries."""
    targets = [
        ROOT / "kakumi_app/pages/admin/athletes_page.py",
        ROOT / "kakumi_app/pages/admin/referees_page.py",
    ]
    for file_path in targets:
        content = file_path.read_text(encoding="utf-8")
        assert "def athletes_table" not in content
        assert "def referees_table" not in content
        assert "rx.table.root" not in content
        assert "sidebar(" not in content


@pytest.mark.parametrize(
    ("route", "module_path", "expected_redirect"),
    [
        pytest.param(
            "/admin/athletes/new",
            "kakumi_app.pages.admin.athletes_page",
            "/registries/athletes",
            id="athletes_new",
        ),
        pytest.param(
            "/admin/referees/new",
            "kakumi_app.pages.admin.referees_page",
            "/registries/referees",
            id="referees_new",
        ),
        pytest.param(
            "/admin/athletes",
            "kakumi_app.pages.admin.athletes_page",
            "/registries/athletes",
            id="athletes_base",
        ),
        pytest.param(
            "/admin/referees",
            "kakumi_app.pages.admin.referees_page",
            "/registries/referees",
            id="referees_base",
        ),
    ],
)
def test_admin_routes_redirect_to_shared_registries(
    route: str,
    module_path: str,
    expected_redirect: str,
) -> None:
    """Admin routes must redirect to shared registries pages."""
    sys.modules.pop(module_path, None)
    importlib.import_module(module_path)

    config = _route_config(route)
    on_load = config.get("on_load")

    if isinstance(on_load, list):
        redirect_spec = on_load[1]
    else:
        redirect_spec = on_load

    assert _redirect_path(redirect_spec) == expected_redirect


@pytest.mark.parametrize(
    ("route", "module_path"),
    [
        pytest.param(
            "/admin/athletes/new",
            "kakumi_app.pages.admin.athletes_page",
            id="athletes_new_init",
        ),
        pytest.param(
            "/admin/referees/new",
            "kakumi_app.pages.admin.referees_page",
            id="referees_new_init",
        ),
    ],
)
def test_admin_new_routes_initialize_create_flow_before_redirect(
    route: str,
    module_path: str,
) -> None:
    """New admin routes must initialize create flow before redirecting."""
    sys.modules.pop(module_path, None)
    importlib.import_module(module_path)

    config = _route_config(route)
    on_load = config.get("on_load")

    assert isinstance(on_load, list)
    assert on_load[0].args[0][1]._var_value is None


def test_registries_page_registers_tournaments_route() -> None:
    """Shared registries page must keep tournaments route registered."""
    sys.modules.pop("kakumi_app.pages.registries", None)
    importlib.import_module("kakumi_app.pages.registries")

    tournaments_cfg = _route_config("/registries/tournaments")

    assert tournaments_cfg.get("route") == "/registries/tournaments"
