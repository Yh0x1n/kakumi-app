"""
KAKUMI
Módulo de puntuación de Kata
"""

import reflex as rx


class JudgesState(rx.State):
    score_fields: list[str] = ["J1", "J2", "J3", "J4", "J5"]


def judge_panel() -> rx.Component:
    return rx.hstack(
        rx.foreach(
            JudgesState.score_fields,
            lambda field: rx.input(
                placeholder=field,
                width="95px",
                height="75px",
                font_size="45px",
                text_align="center",
            ),
        )
    )


def kata_scoreboard() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading("KATA", size="9"),
            rx.vstack(
                rx.text("ATLETA", size="8", as_="label"),
                judge_panel(),
                bg="gray",
                align="center",
            ),
            align="center",
        )
    )
