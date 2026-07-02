"""Round column component for bracket page."""

from __future__ import annotations

import reflex as rx

from kakumi_app.components.match_card import match_card
from kakumi_app.utils import BracketRoundData, MatchCardData


def bracket_round(
    round_data: BracketRoundData,
    show_scores: bool = False,
) -> rx.Component:
    """Render one bracket round column."""
    matches = round_data["matches"].to(list[MatchCardData])
    return rx.box(
        rx.vstack(
            rx.heading(f"Ronda {round_data['round']}", size="4"),
            rx.foreach(
                matches,
                lambda m: match_card(m, show_scores=show_scores),
            ),
            spacing="4",
            align="stretch",
        ),
        min_width="260px",
        width="100%",
    )
