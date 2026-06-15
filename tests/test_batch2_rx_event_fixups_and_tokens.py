"""Batch 2 Reflex event fixups and token migration tests (strict TDD)."""

from __future__ import annotations

import ast
import inspect
import re
from datetime import datetime
from pathlib import Path

import pytest
from reflex.event import EventSpec
from reflex.event import EventHandler

from kakumi_app.states.auth_state import AuthState
from kakumi_app.states.export_state import ExportState
from kakumi_app.states.import_state import ImportState
from kakumi_app.states.viewer_state import ViewerState
from kakumi_app.styles import tokens


ROOT = Path(__file__).resolve().parents[1]
HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def _event_fn(cls: type, method_name: str):
    handler = getattr(cls, method_name)
    assert isinstance(handler, EventHandler)
    assert callable(handler.fn)
    return handler.fn


def _hex_literals_in_file(file_path: Path) -> list[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if HEX_RE.match(node.value):
                found.append(node.value)
    return found


def _event_args_map(event: EventSpec) -> dict[str, object]:
    args_map: dict[str, object] = {}
    for key_var, value in event.args:
        key = getattr(key_var, "_js_expr", "")
        if isinstance(key, str) and key:
            args_map[key] = value
    return args_map


def _is_toast_event(event: EventSpec) -> bool:
    args_map = _event_args_map(event)
    function_arg = args_map.get("function")
    function_expr = getattr(function_arg, "_js_expr", "")
    return "__toast" in function_expr


def test_required_handlers_are_event_handlers() -> None:
    required = [
        (ExportState, "export_tournament_results"),
        (ExportState, "download_export"),
        (ExportState, "clear_export"),
        (ImportState, "import_athletes"),
        (ImportState, "reset_import"),
    ]
    for cls, method_name in required:
        _event_fn(cls, method_name)


def test_export_handlers_are_async_events() -> None:
    for method_name in ["export_tournament_results", "download_export"]:
        fn = _event_fn(ExportState, method_name)
        assert inspect.iscoroutinefunction(fn)


@pytest.mark.anyio
async def test_check_session_timeout_no_longer_returns_bool() -> None:
    state = AuthState()
    state.is_authenticated = True
    state.last_activity = datetime.utcnow().isoformat()

    result = await AuthState.check_session_timeout.fn(state)

    assert result is None
    assert state.session_expired is False


def test_validate_tournament_access_sets_error_state_without_return() -> None:
    state = ViewerState()

    result = ViewerState.validate_tournament_access.fn(state, 999)

    assert isinstance(result, EventSpec)
    assert _is_toast_event(result)
    assert state.access_denied is True


def test_auth_state_permission_contract_uses_private_helper_and_vars() -> None:
    assert not hasattr(AuthState, "has_permission")

    state = AuthState()
    state.is_authenticated = True
    state.user_role = "ADMIN"

    assert state._has_permission("ADMIN") is True
    assert state._has_permission("OPERATOR") is True
    assert state._has_permission("VIEWER") is True
    assert state.is_admin is True
    assert state.is_operator is True


def test_new_tokens_exist_for_batch2() -> None:
    assert tokens.BRAND_RED_HOVER_LIGHT == "#7a3838"
    assert tokens.BG_PAGE == "#f5f5f5"
    assert tokens.BG_CARD_ALT == "#f0f0f0"
    assert tokens.BORDER_LIGHT == "#aaaaaa"
    assert tokens.BG_CODE_PREVIEW == "#f9f9f9"


def test_batch2_target_files_have_no_raw_hex_literals() -> None:
    targets = [
        ROOT / "kakumi_app/components/registries_items.py",
        ROOT / "kakumi_app/pages/auth/login.py",
        ROOT / "kakumi_app/pages/admin/export_page.py",
        ROOT / "kakumi_app/pages/viewer.py",
        ROOT / "kakumi_app/kakumi_app.py",
    ]
    for file_path in targets:
        assert _hex_literals_in_file(file_path) == []
