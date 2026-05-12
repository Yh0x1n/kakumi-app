"""Live match pages for Kumite and Kata routes."""

from __future__ import annotations

import reflex as rx

from kakumi_app.components.kumite_scoreboard import kumite_scoreboard
from kakumi_app.components.kata_scoreboard import kata_scoreboard


def live_match_page() -> rx.Component:
    """Render real live-match scoring page using KumiteMatchState."""
    return rx.container(
        rx.vstack(
            rx.heading("Combate en vivo", size="7"),
            kumite_scoreboard(),
            spacing="5",
            width="100%",
            align="stretch",
        ),
        max_width="1400px",
        padding_y="6",
    )


def kata_live_match_page() -> rx.Component:
    """Render dedicated live Kata page using KataMatchState."""
    return rx.container(
        rx.vstack(
            rx.heading("Kata en vivo", size="7"),
            kata_scoreboard(),
            spacing="5",
            width="100%",
            align="stretch",
        ),
        max_width="1400px",
        padding_y="6",
    )
