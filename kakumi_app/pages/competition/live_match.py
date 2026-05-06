"""Live Kumite match page bound to real route match id."""

from __future__ import annotations

import reflex as rx

from kakumi_app.components.kumite_scoreboard import kumite_scoreboard


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
