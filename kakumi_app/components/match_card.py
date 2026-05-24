"""Reusable match summary card for competition UI."""

from __future__ import annotations

import reflex as rx

from kakumi_app.styles.tokens import TEXT_TERTIARY
from kakumi_app.utils import MatchCardData


def _optional_label(value: rx.Var | str | None) -> rx.Component:
    """Render a safe placeholder when an optional label is missing."""
    return rx.cond(value, rx.text(value), rx.text("—"))


def match_card(match: MatchCardData, show_future_action: bool = False) -> rx.Component:
    """Render a compact operator-facing match card."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.badge(match["status"], color_scheme="gray"),
                rx.spacer(),
                rx.text(
                    f"Ronda {match['round']} · Posición {match['position']}",
                    font_size="sm",
                ),
                width="100%",
                align="center",
            ),
            rx.text(match["aka_label"], font_weight="bold"),
            rx.text("vs", color=TEXT_TERTIARY),
            rx.text(match["ao_label"], font_weight="bold"),
            rx.hstack(
                rx.text("Tatami:", font_weight="medium"),
                _optional_label(match["tatami_label"]),
                spacing="2",
            ),
            rx.hstack(
                rx.text("Árbitro:", font_weight="medium"),
                _optional_label(match["referee_label"]),
                spacing="2",
            ),
            rx.cond(
                show_future_action,
                rx.cond(
                    match["live_match_href"],
                    rx.button(
                        "Iniciar encuentro",
                        width="100%",
                        on_click=rx.redirect(match["live_match_href"]),
                    ),
                    rx.button("Próxima versión", disabled=True, width="100%"),
                ),
            ),
            spacing="3",
            width="100%",
            align="start",
        ),
        width="100%",
    )
