"""Read-only fullscreen Kumite public display component."""

from __future__ import annotations

import reflex as rx

from kakumi_app.states.secondary_display_state import SecondaryDisplayState


def public_kumite_display() -> rx.Component:
    """Render kumite snapshot optimized for projector/fullscreen readability."""

    return rx.box(
        rx.vstack(
            rx.text("KUMITE", font_size="4vw", font_weight="bold"),
            # rx.text(SecondaryDisplayState.kumite_title, font_size="2.2vw"),
            rx.hstack(
                rx.vstack(
                    rx.text("AKA", font_size="2vw", color="red"),
                    rx.text(SecondaryDisplayState.kumite_aka_name, font_size="2vw"),
                    rx.text(
                        SecondaryDisplayState.kumite_aka_score,
                        font_size="7vw",
                        weight="bold",
                    ),
                    rx.badge(
                        rx.cond(
                            SecondaryDisplayState.kumite_aka_senshu,
                            "SENSHU",
                            "Sin senshu",
                        ),
                        color_scheme=rx.cond(
                            SecondaryDisplayState.kumite_aka_senshu,
                            "yellow",
                            "gray",
                        ),
                        size="2",
                    ),
                    rx.text(
                        rx.text.strong("Penalizaciones: "),
                        SecondaryDisplayState.kumite_aka_penalties_label,
                        font_size="1.4vw",
                    ),
                    align="center",
                    spacing="2",
                    width="40vw",
                    bg="red",
                    border_radius="5px",
                ),
                rx.vstack(
                    rx.text(
                        SecondaryDisplayState.kumite_timer_formatted, font_size="6vw"
                    ),
                    rx.text("Solo lectura", font_size="1.5vw", color="gray"),
                    align="center",
                    width="20vw",
                ),
                rx.vstack(
                    rx.text("AO", font_size="2vw", color="blue"),
                    rx.text(SecondaryDisplayState.kumite_ao_name, font_size="2vw"),
                    rx.text(
                        SecondaryDisplayState.kumite_ao_score,
                        font_size="7vw",
                        weight="bold",
                    ),
                    rx.badge(
                        rx.cond(
                            SecondaryDisplayState.kumite_ao_senshu,
                            "SENSHU",
                            "Sin senshu",
                        ),
                        color_scheme=rx.cond(
                            SecondaryDisplayState.kumite_ao_senshu,
                            "yellow",
                            "gray",
                        ),
                        size="2",
                    ),
                    rx.text(
                        rx.text.strong("Penalizaciones: "),
                        SecondaryDisplayState.kumite_ao_penalties_label,
                        font_size="1.4vw",
                    ),
                    align="center",
                    spacing="2",
                    width="40vw",
                    bg="blue",
                    border_radius="5px",
                ),
                width="100%",
                justify="between",
                align="center",
            ),
            width="100%",
            height="100vh",
            justify="center",
            align="center",
            spacing="5",
        ),
        width="100vw",
        height="100vh",
        bg="black",
        color="white",
        padding="2vh",
    )
