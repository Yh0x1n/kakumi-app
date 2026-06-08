"""Reusable calendar popover component for date selection.

Uses only built-in Reflex primitives. Zero external dependencies.
"""

from __future__ import annotations

from typing import Any

import reflex as rx

from kakumi_app.states.tournament_crud_state import TournamentCrudState


# ── Spanish weekday abbreviations ──
_WEEKDAYS = ["Do", "Lu", "Ma", "Mi", "Ju", "Vi", "Sá"]


def _make_on_click(day: int):
    """Factory function to avoid closure capture in rx.foreach."""
    return lambda: TournamentCrudState.select_calendar_day(day)


def _render_day_cell(cell: dict[str, Any]) -> rx.Component:
    """Render a single day cell (button or empty placeholder)."""
    return rx.cond(
        cell["is_current_month"],
        rx.button(
            cell["label"],
            on_click=_make_on_click(cell["day"]),
            width="32px",
            height="32px",
            padding="0",
            font_size="14px",
            variant="surface",
            background_color=rx.cond(
                cell["is_selected"],
                "#c53030",
                "transparent",
            ),
            color=rx.cond(cell["is_selected"], "white", "black"),
            _hover={"background_color": "#e0e0e0"},
        ),
        rx.box("", width="32px", height="32px"),
    )


def date_calendar_popover(
    *,
    value: str | rx.Var[str],
    target: str,
    on_change: rx.EventHandler | None = None,
) -> rx.Component:
    """Render a date field with calendar popover.

    Uses state.calendar_day_cells @rx.var for reactive day grid.
    Uses state.calendar_month_name @rx.var for the nav header.

    Args:
        value: Current date DD/MM/YYYY bound to state var.
        target: 'start' or 'end' for calendar_target disambiguation.
        on_change: Deprecated, kept for backward compatibility.

    Returns:
        Reflex component: trigger button + conditional overlay.
    """
    state = TournamentCrudState

    # Visibility: only when show_calendar AND target matches
    is_visible = rx.cond(
        state.show_calendar & (state.calendar_target == target),
        True,
        False,
    )

    # Month navigation header
    nav_header = rx.hstack(
        rx.button(
            "\u2039",
            on_click=state.calendar_prev_month,
            variant="ghost",
            padding="0 8px",
        ),
        rx.text(state.calendar_month_name, " ", state.calendar_year),
        rx.button(
            "\u203a",
            on_click=state.calendar_next_month,
            variant="ghost",
            padding="0 8px",
        ),
        width="100%",
        justify="between",
        padding="4px 0",
    )

    # Weekday header row
    weekday_headers = rx.grid(
        rx.foreach(
            _WEEKDAYS,
            lambda wd: rx.box(
                rx.text(wd, font_size="12px", text_align="center"),
                width="32px",
            ),
        ),
        grid_template_columns="repeat(7, 1fr)",
        width="100%",
    )

    # Day grid using @rx.var computed cells
    day_grid = rx.grid(
        rx.foreach(state.calendar_day_cells, _render_day_cell),
        grid_template_columns="repeat(7, 1fr)",
        width="100%",
    )

    # Full-viewport backdrop (click outside to close)
    backdrop = rx.box(
        position="fixed",
        top="0",
        left="0",
        width="100vw",
        height="100vh",
        z_index="99",
        on_click=state.close_calendar,
    )

    # Calendar overlay
    calendar_box = rx.box(
        rx.vstack(nav_header, weekday_headers, day_grid, spacing="1"),
        position="absolute",
        z_index="100",
        background_color="white",
        border="1px solid #ddd",
        border_radius="8px",
        padding="8px",
        box_shadow="0 4px 12px rgba(0,0,0,0.15)",
        width="auto",
    )

    # Overlay wrapper: backdrop + calendar
    overlay = rx.box(
        backdrop,
        calendar_box,
        position="relative",
    )

    # Trigger button (styled like input field)
    trigger = rx.button(
        rx.cond(
            value != "",
            rx.text(value, color="black", font_family="inherit", font_size="16px"),
            rx.text(
                "DD/MM/AAAA", color="#999", font_family="inherit", font_size="16px"
            ),
        ),
        on_click=lambda: state.toggle_calendar(target),
        variant="surface",
        width="100%",
        justify="start",
        padding="8px 12px",
        style={
            "border": "1px solid black",
            "background_color": "white",
            "cursor": "pointer",
        },
    )

    # Trigger + conditional overlay
    return rx.box(
        rx.vstack(
            trigger,
            rx.cond(is_visible, overlay),
            spacing="1",
            position="relative",
        ),
        position="relative",
    )
