"""
KAKUMI
Módulo de puntuación de Kata
"""

import reflex as rx


def kata_scoreboard() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading("KATA", size="9"),
            rx.vstack(
                rx.text("AKA", size="8", as_="label"),
                width="100%",
                bg="red",
                align="start",
                border_radius="5px",
            ),
            rx.vstack(
                rx.text("AO", size="8", as_="label"),
                width="100%",
                bg="blue",
                align="end",
                border_radius="5px",
            ),
        )
    )
