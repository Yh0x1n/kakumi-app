"""Informal Kata standings table component."""

from __future__ import annotations

from typing import Any

import reflex as rx


def _standings_row(row: dict[str, Any]) -> rx.Component:
    """Render one standings row."""
    return rx.table.row(
        rx.table.cell(row["rank"]),
        rx.table.cell(row["athlete_name"]),
        rx.table.cell(row["final_score"]),
        rx.table.cell(
            rx.cond(
                row["needs_extra_kata"],
                rx.badge("Extra kata", color_scheme="amber"),
                rx.badge("OK", color_scheme="green"),
            )
        ),
    )


def kata_informal_table(standings: list[dict[str, Any]]) -> rx.Component:
    """Render table-first view for informal Kata rankings."""
    return rx.vstack(
        rx.heading("Ranking informal", size="5"),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("#"),
                    rx.table.column_header_cell("Atleta"),
                    rx.table.column_header_cell("Puntaje"),
                    rx.table.column_header_cell("Estado"),
                )
            ),
            rx.table.body(
                rx.foreach(
                    standings,
                    lambda row: _standings_row(row),
                )
            ),
            width="100%",
        ),
        width="100%",
        align="start",
        spacing="3",
    )
