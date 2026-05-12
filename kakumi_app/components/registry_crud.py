"""Shared CRUD components for registries pages."""

from __future__ import annotations

from typing import Any, Callable

import reflex as rx

from kakumi_app.components.sidebar import sidebar
from kakumi_app.styles.tokens import BG_PAGE, BORDER_LIGHT, BRAND_RED, BRAND_RED_HOVER

CARD_BG = "#ffffff"
HEADER_BG = "#f2f2f2"
MUTED_TEXT = "#534342"


def registry_page_shell(*, body: rx.Component) -> rx.Component:
    """Reusable shell with sidebar and centered content."""
    return rx.box(
        rx.hstack(
            sidebar(),
            rx.box(
                body,
                width="100%",
                max_width="1280px",
                margin_x="auto",
                padding_x={"base": "16px", "md": "40px"},
                padding_y="24px",
            ),
            width="100%",
            align="start",
            spacing="0",
        ),
        width="100%",
        min_height="100vh",
        background_color=BG_PAGE,
    )


def registry_actions_header(
    *,
    title: str,
    subtitle: str,
    add_label: str,
    on_add_click: Any,
    on_import_click: Any = None,
    on_export_click: Any = None,
    import_label: str = "Importar",
    export_label: str = "Exportar",
) -> rx.Component:
    """Header with page copy and action group aligned to screenshot."""
    return rx.hstack(
        rx.vstack(
            rx.heading(title, size="8", color="#1a1c1c"),
            rx.text(subtitle, color=MUTED_TEXT),
            spacing="1",
            align="start",
        ),
        rx.hstack(
            rx.button(
                import_label,
                on_click=on_import_click,
                disabled=on_import_click is None,
                variant="outline",
                color=BRAND_RED,
                border=f"1.5px solid {BRAND_RED}",
            ),
            rx.button(
                export_label,
                on_click=on_export_click,
                disabled=on_export_click is None,
                variant="outline",
                color=BRAND_RED,
                border=f"1.5px solid {BRAND_RED}",
            ),
            rx.button(
                add_label,
                on_click=on_add_click,
                background_color=BRAND_RED,
                _hover={"background_color": BRAND_RED_HOVER},
                color="white",
            ),
            spacing="2",
            wrap="wrap",
            justify="end",
        ),
        width="100%",
        justify="between",
        align={"base": "start", "md": "center"},
        direction={"base": "column", "md": "row"},
        spacing="4",
        margin_bottom="24px",
    )


def registry_table_filters(
    *,
    search_placeholder: str,
    on_search_change: Any,
    on_search_click: Any,
    result_label: str,
) -> rx.Component:
    """Search/filter row inside the card."""
    return rx.hstack(
        rx.hstack(
            rx.input(
                placeholder=search_placeholder,
                on_change=on_search_change,
                width={"base": "100%", "md": "420px"},
                background_color=BG_PAGE,
                border=f"1px solid {BORDER_LIGHT}",
            ),
            rx.button(
                "Buscar",
                on_click=on_search_click,
                variant="soft",
                color=BRAND_RED,
            ),
            spacing="2",
            width="100%",
            wrap="wrap",
        ),
        rx.text(result_label, size="2", color=MUTED_TEXT),
        width="100%",
        justify="between",
        align="center",
        direction={"base": "column", "md": "row"},
        spacing="3",
        padding="16px",
        border_bottom=f"1px solid {BORDER_LIGHT}",
    )


def registry_error(error_var: Any) -> rx.Component:
    """Shared inline error callout for CRUD forms/tables."""
    return rx.cond(
        error_var,
        rx.callout(error_var, icon="triangle_alert", color_scheme="red"),
    )


def registry_empty_state(
    *,
    icon: str,
    title: str,
    subtitle: str,
    cta_label: str,
    on_cta_click: Any,
) -> rx.Component:
    """Centered empty state shown when there are no rows."""
    return rx.vstack(
        rx.box(
            rx.text(icon, font_size="30px"),
            width="64px",
            height="64px",
            border_radius="9999px",
            background_color="#e8e8e8",
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        rx.heading(title, size="6"),
        rx.text(subtitle, color=MUTED_TEXT, text_align="center", max_width="560px"),
        rx.button(
            cta_label,
            on_click=on_cta_click,
            background_color=BRAND_RED,
            _hover={"background_color": BRAND_RED_HOVER},
            color="white",
        ),
        spacing="4",
        align="center",
        justify="center",
        min_height="320px",
        padding="24px",
    )


def registry_table(
    *,
    headers: list[str],
    rows_var: Any,
    row_renderer: Callable[[Any], rx.Component],
    empty_state: rx.Component,
) -> rx.Component:
    """Shared table skeleton with sticky-like gray header and empty state."""
    return rx.cond(
        rows_var,
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        *[
                            rx.table.column_header_cell(
                                header,
                                color=MUTED_TEXT,
                                background_color=HEADER_BG,
                            )
                            for header in headers
                        ]
                    )
                ),
                rx.table.body(rx.foreach(rows_var, row_renderer)),
                width="100%",
                variant="surface",
                style={"border": "none"},
            ),
            width="100%",
            overflow_x="auto",
        ),
        empty_state,
    )


def registry_pagination_footer(*, summary_label: str) -> rx.Component:
    """Footer area matching screenshot pagination baseline."""
    return rx.hstack(
        rx.text(summary_label, size="2", color=MUTED_TEXT),
        rx.hstack(
            rx.button("‹", size="1", disabled=True, variant="ghost"),
            rx.button("›", size="1", disabled=True, variant="ghost"),
            spacing="1",
        ),
        width="100%",
        justify="between",
        align="center",
        padding="14px 16px",
        border_top=f"1px solid {BORDER_LIGHT}",
    )


def registry_table_card(
    *,
    filters: rx.Component,
    table: rx.Component,
    footer: rx.Component,
) -> rx.Component:
    """Bordered card container for search row, table and footer."""
    return rx.box(
        filters,
        table,
        footer,
        width="100%",
        border=f"1px solid {BORDER_LIGHT}",
        border_radius="12px",
        background_color=CARD_BG,
        overflow="hidden",
    )
