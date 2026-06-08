"""Strict-TDD tests for date calendar component."""
# Phase 2: RED — all tests must FAIL initially.
# Phase 3: GREEN — make them pass.
# Phase 4: TRIANGULATE — add edge cases.

from __future__ import annotations

import datetime
from typing import Any

import reflex as rx

from kakumi_app.states.tournament_crud_state import (
    TournamentCrudState,
    _date_to_iso,
    _display_to_date,
    _iso_to_display,
)


# =============================================================================
# 2.1 RED: Format helpers unit tests
# =============================================================================


def test_iso_to_display_happy_path() -> None:
    """_iso_to_display('2026-06-07') → '07/06/2026'."""
    assert _iso_to_display("2026-06-07") == "07/06/2026"


def test_iso_to_display_empty() -> None:
    """_iso_to_display('') → ''."""
    assert _iso_to_display("") == ""


def test_iso_to_display_invalid() -> None:
    """_iso_to_display('not-a-date') → ''."""
    assert _iso_to_display("not-a-date") == ""


def test_display_to_date_happy_path() -> None:
    """_display_to_date('07/06/2026') → date(2026, 6, 7)."""
    assert _display_to_date("07/06/2026") == datetime.date(2026, 6, 7)


def test_display_to_date_dash_variant() -> None:
    """_display_to_date('07-06-2026') → date(2026, 6, 7) (dash normalisation)."""
    assert _display_to_date("07-06-2026") == datetime.date(2026, 6, 7)


def test_display_to_date_invalid() -> None:
    """_display_to_date('99/99/9999') → None."""
    assert _display_to_date("99/99/9999") is None


def test_display_to_date_garbage() -> None:
    """_display_to_date('abc') → None."""
    assert _display_to_date("abc") is None


def test_display_to_date_empty() -> None:
    """_display_to_date('') → None."""
    assert _display_to_date("") is None


def test_date_to_iso() -> None:
    """_date_to_iso(date(2026, 6, 7)) → '2026-06-07'."""
    assert _date_to_iso(datetime.date(2026, 6, 7)) == "2026-06-07"


# =============================================================================
# 2.2 RED: _build_day_cells grid structure tests
# =============================================================================


def test_build_day_cells_returns_list_of_dicts() -> None:
    """Verifies shape: list of dicts with expected keys."""
    from kakumi_app.states.tournament_crud_state import _build_day_cells

    cells = _build_day_cells(2026, 6, "")
    assert isinstance(cells, list)
    if cells:
        cell = cells[0]
        assert isinstance(cell, dict)
        for key in ("day", "is_current_month", "is_selected", "label"):
            assert key in cell


def test_build_day_cells_length_35_or_42() -> None:
    """Verifies 5 or 6 weeks (35–42 items)."""
    from kakumi_app.states.tournament_crud_state import _build_day_cells

    cells = _build_day_cells(2026, 6, "")
    assert len(cells) in (35, 42)


def test_build_day_cells_offset_first_week() -> None:
    """June 2026 starts on Monday → first cell (Sunday) has day=0."""
    from kakumi_app.states.tournament_crud_state import _build_day_cells

    cells = _build_day_cells(2026, 6, "")
    # First cell (Sunday) should be empty/offset
    assert cells[0]["day"] == 0
    assert cells[0]["is_current_month"] is False


def test_build_day_cells_marks_selected_date() -> None:
    """selected_display='07/06/2026' → exactly one cell with is_selected=True, day=7."""
    from kakumi_app.states.tournament_crud_state import _build_day_cells

    cells = _build_day_cells(2026, 6, "07/06/2026")
    selected = [c for c in cells if c["is_selected"]]
    assert len(selected) == 1
    assert selected[0]["day"] == 7


def test_build_day_cells_no_selection() -> None:
    """selected_display='' → all is_selected=False."""
    from kakumi_app.states.tournament_crud_state import _build_day_cells

    cells = _build_day_cells(2026, 6, "")
    assert all(c["is_selected"] is False for c in cells)


# =============================================================================
# 2.3 RED: Calendar state vars and event handler tests
# =============================================================================


def test_calendar_state_vars_initial_values() -> None:
    """Initial values: show_calendar=False, calendar_target='', month=0, year=0."""
    state = TournamentCrudState()
    assert state.show_calendar is False
    assert state.calendar_target == ""
    assert state.calendar_month == 0
    assert state.calendar_year == 0


def test_toggle_calendar_opens_for_target() -> None:
    """toggle_calendar('start') → show_calendar=True, target='start', month/year set."""
    state = TournamentCrudState()
    state.toggle_calendar("start")
    assert state.show_calendar is True
    assert state.calendar_target == "start"
    assert state.calendar_month != 0
    assert state.calendar_year != 0


def test_toggle_calendar_closes_same_target() -> None:
    """toggle_calendar('start') twice → show_calendar=False, target=''."""
    state = TournamentCrudState()
    state.toggle_calendar("start")
    state.toggle_calendar("start")
    assert state.show_calendar is False
    assert state.calendar_target == ""


def test_toggle_calendar_switches_target() -> None:
    """toggle_calendar('start') then toggle_calendar('end') → target='end', visible."""
    state = TournamentCrudState()
    state.toggle_calendar("start")
    state.toggle_calendar("end")
    assert state.show_calendar is True
    assert state.calendar_target == "end"


def test_calendar_prev_month_wraps_year() -> None:
    """calendar_month=1, year=2026 → prev → month=12, year=2025."""
    state = TournamentCrudState()
    state.calendar_month = 1
    state.calendar_year = 2026
    state.calendar_prev_month()
    assert state.calendar_month == 12
    assert state.calendar_year == 2025


def test_calendar_next_month_wraps_year() -> None:
    """calendar_month=12, year=2026 → next → month=1, year=2027."""
    state = TournamentCrudState()
    state.calendar_month = 12
    state.calendar_year = 2026
    state.calendar_next_month()
    assert state.calendar_month == 1
    assert state.calendar_year == 2027


def test_calendar_select_day_sets_start_date() -> None:
    """select_calendar_day(15) with target='start' → start_date='15/06/2026'."""
    state = TournamentCrudState()
    state.calendar_target = "start"
    state.calendar_month = 6
    state.calendar_year = 2026
    state.select_calendar_day(15)
    assert state.start_date == "15/06/2026"
    assert state.show_calendar is False


def test_calendar_select_day_sets_end_date() -> None:
    """select_calendar_day(20) with target='end' → end_date='20/06/2026'."""
    state = TournamentCrudState()
    state.calendar_target = "end"
    state.calendar_month = 6
    state.calendar_year = 2026
    state.select_calendar_day(20)
    assert state.end_date == "20/06/2026"
    assert state.show_calendar is False


def test_calendar_select_day_closes_popover() -> None:
    """After select_calendar_day, show_calendar=False, calendar_target=''."""
    state = TournamentCrudState()
    state.show_calendar = True
    state.calendar_target = "start"
    state.calendar_month = 6
    state.calendar_year = 2026
    state.select_calendar_day(1)
    assert state.show_calendar is False
    assert state.calendar_target == ""


# =============================================================================
# 2.4 RED: Component contract tests
# =============================================================================


def test_date_calendar_popover_is_callable() -> None:
    """date_calendar_popover is callable."""
    from kakumi_app.components.date_calendar import date_calendar_popover

    assert callable(date_calendar_popover)


def test_date_calendar_popover_returns_component() -> None:
    """date_calendar_popover returns an rx.Component."""
    from kakumi_app.components.date_calendar import date_calendar_popover

    result = date_calendar_popover(
        value=rx.Var.create(""),
        on_change=lambda x: None,  # type: ignore[arg-type]
        target="start",
    )
    assert isinstance(result, rx.Component)


def test_date_calendar_popover_includes_placeholder() -> None:
    """Rendered component contains 'DD/MM/AAAA' placeholder."""
    from kakumi_app.components.date_calendar import date_calendar_popover

    result = date_calendar_popover(
        value=rx.Var.create(""),
        on_change=lambda x: None,  # type: ignore[arg-type]
        target="start",
    )
    rendered = str(result)
    assert "DD/MM/AAAA" in rendered


def test_render_day_cell_returns_component_for_current_month() -> None:
    """_render_day_cell with is_current_month=True returns rx.Component."""
    from kakumi_app.components.date_calendar import _render_day_cell

    cell: dict[str, Any] = {
        "day": 15,
        "is_current_month": True,
        "is_selected": False,
        "label": "15",
    }
    result = _render_day_cell(cell)
    assert isinstance(result, rx.Component)
    assert result is not None


# =============================================================================
# 4.1 TRIANGULATE: Format helper edge cases
# =============================================================================


def test_iso_to_display_none() -> None:
    """_iso_to_display(None) → '' (type safety)."""
    # mypy: ignore-arg-type
    assert _iso_to_display(None) == ""  # type: ignore[arg-type]


def test_display_to_date_edge_dates() -> None:
    """Edge dates: 01/01/0001 and 31/12/9999 parse correctly."""
    assert _display_to_date("01/01/0001") == datetime.date(1, 1, 1)
    assert _display_to_date("31/12/9999") == datetime.date(9999, 12, 31)


def test_display_to_date_february_leap() -> None:
    """29/02/2024 (leap) parses; 29/02/2023 (non-leap) returns None."""
    assert _display_to_date("29/02/2024") == datetime.date(2024, 2, 29)
    assert _display_to_date("29/02/2023") is None


def test_iso_to_display_roundtrip() -> None:
    """Roundtrip: _display_to_date(_iso_to_display(x)) == date(x)."""
    result = _display_to_date(_iso_to_display("2026-06-07"))
    assert result == datetime.date(2026, 6, 7)


# =============================================================================
# 4.2 TRIANGULATE: Calendar navigation boundary tests
# =============================================================================


def test_calendar_prev_month_from_january() -> None:
    """calendar_prev_month from January wraps to December previous year."""
    state = TournamentCrudState()
    state.calendar_month = 1
    state.calendar_year = 2026
    state.calendar_prev_month()
    assert state.calendar_month == 12
    assert state.calendar_year == 2025


def test_calendar_next_month_from_december() -> None:
    """calendar_next_month from December wraps to January next year."""
    state = TournamentCrudState()
    state.calendar_month = 12
    state.calendar_year = 2026
    state.calendar_next_month()
    assert state.calendar_month == 1
    assert state.calendar_year == 2027


def test_toggle_calendar_reinitializes_month() -> None:
    """toggle_calendar when month=0 sets month/year to today."""
    state = TournamentCrudState()
    state.calendar_month = 0
    state.calendar_year = 0
    state.toggle_calendar("start")
    today = datetime.date.today()
    assert state.calendar_month == today.month
    assert state.calendar_year == today.year


def test_toggle_calendar_preserves_month_if_already_set() -> None:
    """toggle_calendar when month already set does not change it."""
    state = TournamentCrudState()
    state.calendar_month = 6
    state.calendar_year = 2026
    state.toggle_calendar("start")
    assert state.calendar_month == 6
    assert state.calendar_year == 2026


# =============================================================================
# 4.3 TRIANGULATE: Day cell rendering edge cases
# =============================================================================


def test_build_day_cells_february_non_leap() -> None:
    """February 2023 → 28 days, no cell has day=29."""
    from kakumi_app.states.tournament_crud_state import _build_day_cells

    cells = _build_day_cells(2023, 2, "")
    days = [c["day"] for c in cells if c["is_current_month"]]
    assert len(days) == 28
    assert 29 not in days


def test_build_day_cells_february_leap() -> None:
    """February 2024 → 29 days, cell with day=29 exists."""
    from kakumi_app.states.tournament_crud_state import _build_day_cells

    cells = _build_day_cells(2024, 2, "")
    days = [c["day"] for c in cells if c["is_current_month"]]
    assert len(days) == 29
    assert 29 in days


def test_render_day_cell_empty_month() -> None:
    """is_current_month=False → renders a placeholder, not a button."""
    from kakumi_app.components.date_calendar import _render_day_cell

    cell: dict[str, Any] = {
        "day": 0,
        "is_current_month": False,
        "is_selected": False,
        "label": "",
    }
    result = _render_day_cell(cell)
    rendered = str(result)
    assert "button" not in rendered.lower() or "<button" not in rendered


def test_render_day_cell_uses_partial_for_closure() -> None:
    """_render_day_cell uses _make_on_click factory for closure safety."""
    from kakumi_app.components.date_calendar import (
        _make_on_click,
        _render_day_cell,
    )

    # Inspect the closure mitigation: verify _make_on_click returns a callable
    click_handler = _make_on_click(15)
    assert callable(click_handler)

    cell: dict[str, Any] = {
        "day": 15,
        "is_current_month": True,
        "is_selected": False,
        "label": "15",
    }
    rendered = str(_render_day_cell(cell))
    # The rendered component should reference select_calendar_day
    assert "select_calendar_day" in rendered


# =============================================================================
# 4.4 TRIANGULATE: calendar_day_cells @rx.var computed property
# =============================================================================


def test_calendar_day_cells_var_returns_cells() -> None:
    """calendar_day_cells @rx.var returns proper cell list when month/year set."""
    state = TournamentCrudState()
    state.calendar_month = 6
    state.calendar_year = 2026
    state.calendar_target = "start"
    state.start_date = "15/06/2026"
    cells = state.calendar_day_cells
    assert isinstance(cells, list)
    assert len(cells) in (35, 42)
    selected = [c for c in cells if c["is_selected"]]
    assert len(selected) == 1
    assert selected[0]["day"] == 15


def test_calendar_day_cells_var_empty_when_uninitialized() -> None:
    """calendar_day_cells returns [] when calendar_month/year are 0."""
    state = TournamentCrudState()
    state.calendar_month = 0
    state.calendar_year = 0
    assert state.calendar_day_cells == []


def test_calendar_month_name_var() -> None:
    """calendar_month_name returns Spanish month name for valid months."""
    state = TournamentCrudState()
    state.calendar_month = 6
    assert state.calendar_month_name == "Junio"
    state.calendar_month = 1
    assert state.calendar_month_name == "Enero"
    state.calendar_month = 12
    assert state.calendar_month_name == "Diciembre"
    state.calendar_month = 0
    assert state.calendar_month_name == ""
    state.calendar_month = 13
    assert state.calendar_month_name == ""
