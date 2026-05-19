"""Read-only fullscreen Kata public display component."""

from __future__ import annotations

import reflex as rx

from kakumi_app.states.secondary_display_state import SecondaryDisplayState


def public_kata_display() -> rx.Component:
    """Render kata snapshot optimized for projector/fullscreen readability."""

    return rx.box(
        rx.cond(
            SecondaryDisplayState.kata_is_informal_mode,
            rx.vstack(
                rx.text(
                    SecondaryDisplayState.kata_informal_athlete_name,
                    font_size="4.4vw",
                    font_weight="bold",
                ),
                rx.vstack(
                    rx.text("Resultados", font_size="1.8vw", font_weight="bold"),
                    rx.cond(
                        SecondaryDisplayState.kata_informal_results.length() > 0,
                        rx.foreach(
                            SecondaryDisplayState.kata_informal_results,
                            lambda row: rx.text(row, font_size="1.6vw"),
                        ),
                        rx.text("Sin resultados", font_size="1.6vw"),
                    ),
                    spacing="1",
                    align="center",
                ),
                width="100%",
                height="100vh",
                justify="center",
                align="center",
                spacing="5",
            ),
            rx.vstack(
                rx.text("Kata", font_size="4vw", font_weight="bold"),
                rx.text(SecondaryDisplayState.kata_title, font_size="2.2vw"),
                rx.hstack(
                    rx.vstack(
                        rx.text("AKA", font_size="2vw", color="red"),
                        rx.text(SecondaryDisplayState.kata_aka_name, font_size="2.2vw"),
                        rx.text(
                            SecondaryDisplayState.kata_aka_total,
                            font_size="5vw",
                            weight="bold",
                        ),
                        align="center",
                        spacing="2",
                        width="45vw",
                    ),
                    rx.vstack(
                        rx.text("AO", font_size="2vw", color="blue"),
                        rx.text(SecondaryDisplayState.kata_ao_name, font_size="2.2vw"),
                        rx.text(
                            SecondaryDisplayState.kata_ao_total,
                            font_size="5vw",
                            weight="bold",
                        ),
                        align="center",
                        spacing="2",
                        width="45vw",
                    ),
                    width="100%",
                    justify="between",
                ),
                rx.cond(
                    SecondaryDisplayState.kata_judge_detail_visible,
                    rx.vstack(
                        rx.text("Detalle jueces", font_size="1.8vw", weight="bold"),
                        rx.foreach(
                            SecondaryDisplayState.kata_judge_detail_lines,
                            lambda line: rx.text(line, font_size="1.5vw"),
                        ),
                        spacing="1",
                        align="center",
                    ),
                    rx.fragment(),
                ),
                width="100%",
                height="100vh",
                justify="center",
                align="center",
                spacing="5",
            ),
        ),
        width="100vw",
        height="100vh",
        bg="black",
        color="white",
        padding="2vh",
    )
