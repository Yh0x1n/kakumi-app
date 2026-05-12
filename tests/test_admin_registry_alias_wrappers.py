"""Regression tests for admin registry alias wrappers."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import get_args

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


def test_admin_new_routes_redirect_to_shared_registries_flow() -> None:
    """New admin routes redirect to shared registries pages."""
    sys.modules.pop("kakumi_app.pages.admin.athletes_page", None)
    sys.modules.pop("kakumi_app.pages.admin.referees_page", None)
    importlib.import_module("kakumi_app.pages.admin.athletes_page")
    importlib.import_module("kakumi_app.pages.admin.referees_page")

    athletes_new = _route_config("/admin/athletes/new")
    referees_new = _route_config("/admin/referees/new")

    athletes_on_load = athletes_new.get("on_load")
    referees_on_load = referees_new.get("on_load")

    assert isinstance(athletes_on_load, list)
    assert isinstance(referees_on_load, list)

    assert _redirect_path(athletes_on_load[1]) == "/registries/athletes"
    assert _redirect_path(referees_on_load[1]) == "/registries/referees"


def test_admin_base_routes_redirect_to_shared_registries_flow() -> None:
    """Base admin routes redirect to shared registries pages."""
    sys.modules.pop("kakumi_app.pages.admin.athletes_page", None)
    sys.modules.pop("kakumi_app.pages.admin.referees_page", None)
    importlib.import_module("kakumi_app.pages.admin.athletes_page")
    importlib.import_module("kakumi_app.pages.admin.referees_page")

    athletes_cfg = _route_config("/admin/athletes")
    referees_cfg = _route_config("/admin/referees")

    athletes_on_load = athletes_cfg.get("on_load")
    referees_on_load = referees_cfg.get("on_load")

    assert isinstance(athletes_on_load, rx.event.EventSpec)
    assert isinstance(referees_on_load, rx.event.EventSpec)
    assert _redirect_path(athletes_on_load) == "/registries/athletes"
    assert _redirect_path(referees_on_load) == "/registries/referees"


def test_admin_new_routes_initialize_create_flow_before_redirect() -> None:
    """New admin routes initialize create flow before redirecting."""
    sys.modules.pop("kakumi_app.pages.admin.athletes_page", None)
    sys.modules.pop("kakumi_app.pages.admin.referees_page", None)
    importlib.import_module("kakumi_app.pages.admin.athletes_page")
    importlib.import_module("kakumi_app.pages.admin.referees_page")

    athletes_new = _route_config("/admin/athletes/new")
    referees_new = _route_config("/admin/referees/new")

    athletes_on_load = athletes_new.get("on_load")
    referees_on_load = referees_new.get("on_load")

    assert isinstance(athletes_on_load, list)
    assert isinstance(referees_on_load, list)
    assert athletes_on_load[0].args[0][1]._var_value is None
    assert referees_on_load[0].args[0][1]._var_value is None


def test_registries_page_registers_tournaments_route() -> None:
    """Shared registries page keeps tournaments route registered."""
    sys.modules.pop("kakumi_app.pages.registries", None)
    importlib.import_module("kakumi_app.pages.registries")

    tournaments_cfg = _route_config("/registries/tournaments")

    assert tournaments_cfg.get("route") == "/registries/tournaments"
