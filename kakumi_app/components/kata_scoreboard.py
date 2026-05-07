"""Kata scoreboard bound to KataMatchState."""

import reflex as rx

from kakumi_app.models.tournament_model import Participant
from kakumi_app.states.kata_match_state import KataMatchState


def _judge_input_row(judge_slot: str) -> rx.Component:
    """Render one judge row for numerical mode."""
    return rx.hstack(
        rx.text(judge_slot, width="50px", weight="bold"),
        rx.input(
            placeholder="AKA",
            value=KataMatchState.judge_entries[judge_slot][Participant.AKA.value],
            on_change=lambda value: KataMatchState.set_judge_score(
                judge_slot=judge_slot,
                participant=Participant.AKA.value,
                value=value,
            ),
            width="120px",
            text_align="center",
        ),
        rx.input(
            placeholder="AO",
            value=KataMatchState.judge_entries[judge_slot][Participant.AO.value],
            on_change=lambda value: KataMatchState.set_judge_score(
                judge_slot=judge_slot,
                participant=Participant.AO.value,
                value=value,
            ),
            width="120px",
            text_align="center",
        ),
        width="100%",
        justify="center",
        align="center",
    )


def _judge_vote_row(judge_slot: str) -> rx.Component:
    """Render one judge row for flag mode."""
    return rx.hstack(
        rx.text(judge_slot, width="50px", weight="bold"),
        rx.button(
            "AKA",
            variant=rx.cond(
                KataMatchState.judge_entries[judge_slot]["vote"]
                == Participant.AKA.value,
                "solid",
                "outline",
            ),
            on_click=KataMatchState.set_flag_vote(
                judge_slot=judge_slot,
                vote=Participant.AKA.value,
            ),
            width="120px",
        ),
        rx.button(
            "AO",
            variant=rx.cond(
                KataMatchState.judge_entries[judge_slot]["vote"]
                == Participant.AO.value,
                "solid",
                "outline",
            ),
            on_click=KataMatchState.set_flag_vote(
                judge_slot=judge_slot,
                vote=Participant.AO.value,
            ),
            width="120px",
        ),
        width="100%",
        justify="center",
        align="center",
    )


def kata_scoreboard() -> rx.Component:
    """Render live Kata scoreboard with exhibition/tournament flow."""
    return rx.center(
        rx.vstack(
            rx.cond(
                KataMatchState.is_exhibition_mode,
                rx.badge("Exhibition", color_scheme="orange", size="3"),
                rx.badge("Match Active", color_scheme="green", size="3"),
            ),
            rx.heading("Kata en vivo", size="7"),
            rx.hstack(
                rx.badge(f"Panel: {KataMatchState.judge_panel_size}", size="2"),
                rx.badge(f"Modo: {KataMatchState.scoring_type}", size="2"),
                rx.cond(
                    KataMatchState.is_exhibition_mode,
                    rx.cond(
                        KataMatchState.is_flag_mode,
                        rx.badge(
                            f"Regla: {KataMatchState.decision_rule}",
                            size="2",
                        ),
                        rx.select(
                            ["average-with-discard", "majority-by-judge"],
                            value=KataMatchState.decision_rule,
                            on_change=KataMatchState.set_decision_rule,
                            size="1",
                            width="220px",
                        ),
                    ),
                    rx.badge(
                        f"Regla: {KataMatchState.decision_rule}",
                        size="2",
                    ),
                ),
                spacing="2",
                wrap="wrap",
            ),
            rx.hstack(
                rx.vstack(
                    rx.text("AKA", weight="bold", color="red"),
                    rx.text(KataMatchState.aka_name, size="4"),
                    spacing="1",
                    align="center",
                ),
                rx.vstack(
                    rx.text("AO", weight="bold", color="blue"),
                    rx.text(KataMatchState.ao_name, size="4"),
                    spacing="1",
                    align="center",
                ),
                spacing="6",
                justify="center",
            ),
            rx.cond(
                KataMatchState.is_flag_mode,
                rx.vstack(
                    rx.foreach(KataMatchState.judge_slots, _judge_vote_row),
                    spacing="2",
                    width="100%",
                    align="stretch",
                ),
                rx.vstack(
                    rx.hstack(
                        rx.text("Juez", width="50px", weight="bold"),
                        rx.text("AKA", width="120px", text_align="center"),
                        rx.text("AO", width="120px", text_align="center"),
                        justify="center",
                        width="100%",
                    ),
                    rx.foreach(KataMatchState.judge_slots, _judge_input_row),
                    spacing="2",
                    width="100%",
                    align="stretch",
                ),
            ),
            rx.hstack(
                rx.badge(
                    rx.cond(
                        KataMatchState.panel_complete,
                        "Panel completo",
                        "Panel incompleto",
                    ),
                    color_scheme=rx.cond(
                        KataMatchState.panel_complete,
                        "green",
                        "red",
                    ),
                ),
                spacing="2",
            ),
            rx.hstack(
                rx.button("Finalizar", on_click=KataMatchState.finalize_match),
                rx.button(
                    "Reiniciar panel",
                    variant="outline",
                    on_click=KataMatchState.reset_entries,
                ),
                spacing="2",
            ),
            rx.cond(
                KataMatchState.winner_participant != "",
                rx.badge(
                    f"Ganador: {KataMatchState.winner_participant}",
                    color_scheme="green",
                ),
                rx.fragment(),
            ),
            rx.cond(
                KataMatchState.result_message != "",
                rx.text(KataMatchState.result_message),
                rx.fragment(),
            ),
            rx.cond(
                KataMatchState.error_message != "",
                rx.text(KataMatchState.error_message, color="red"),
                rx.fragment(),
            ),
            spacing="4",
            width="100%",
            align="center",
            max_width="900px",
        )
    )
