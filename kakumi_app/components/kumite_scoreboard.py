"""Scoreboard de Kumite conectado a estado real de match."""

import reflex as rx

from kakumi_app.models.tournament_model import Participant, ScoreType
from kakumi_app.states.kumite_match_state import KumiteMatchState


def _participant_panel(participant: str, color: str, title: str) -> rx.Component:
    """Render one side (AKA/AO) panel bound to KumiteMatchState."""
    is_aka = participant == Participant.AKA.value
    name = rx.cond(is_aka, KumiteMatchState.aka_name, KumiteMatchState.ao_name)
    score = rx.cond(is_aka, KumiteMatchState.aka_score, KumiteMatchState.ao_score)
    slots = rx.cond(
        is_aka,
        KumiteMatchState.aka_penalty_slots,
        KumiteMatchState.ao_penalty_slots,
    )
    senshu = rx.cond(is_aka, KumiteMatchState.aka_senshu, KumiteMatchState.ao_senshu)

    def _slot(label: str) -> rx.Component:
        return rx.vstack(
            rx.heading(label, size="4"),
            rx.checkbox(checked=slots[label], is_disabled=True),
            spacing="1",
            align="center",
        )

    return rx.vstack(
        rx.heading(title, as_="label", size="8"),
        rx.text(name, as_="label", size="6"),
        rx.hstack(
            rx.text("SENSHU", weight="bold"),
            rx.checkbox(checked=senshu, is_disabled=True),
            spacing="2",
            align="center",
        ),
        rx.hstack(
            rx.button(
                "Otorgar SENSHU",
                variant="outline",
                on_click=KumiteMatchState.apply_manual_senshu(participant=participant),
            ),
            rx.button(
                "Revocar SENSHU",
                variant="outline",
                on_click=KumiteMatchState.revoke_manual_senshu(participant=participant),
            ),
            spacing="2",
        ),
        rx.heading(score, as_="div", size="9"),
        rx.hstack(
            rx.button(
                "YUKO",
                on_click=KumiteMatchState.apply_score(
                    participant=participant,
                    score_type=ScoreType.YUKO.value,
                    applied_by_id=1,
                ),
            ),
            rx.button(
                "WAZA-ARI",
                on_click=KumiteMatchState.apply_score(
                    participant=participant,
                    score_type=ScoreType.WAZA_ARI.value,
                    applied_by_id=1,
                ),
            ),
            rx.button(
                "IPPON",
                on_click=KumiteMatchState.apply_score(
                    participant=participant,
                    score_type=ScoreType.IPPON.value,
                    applied_by_id=1,
                ),
            ),
        ),
        rx.hstack(
            _slot("C1"),
            _slot("C2"),
            _slot("C3"),
            _slot("HC"),
            _slot("H"),
            spacing="3",
        ),
        rx.button(
            "Penalización",
            bg="white",
            color="black",
            on_click=KumiteMatchState.apply_penalty_cumulative(participant),
        ),
        bg=color,
        width="50vh",
        align="center",
        padding="3",
    )


def kumite_scoreboard() -> rx.Component:
    """Componente de Scoreboard de kumite con estado real backend."""
    from .timer import timer

    return rx.center(
        rx.vstack(
            rx.cond(
                KumiteMatchState.is_exhibition_mode,
                rx.badge("Exhibition", color_scheme="orange", size="3"),
                rx.badge("Match Active", color_scheme="green", size="3"),
            ),
            rx.hstack(
                _participant_panel(
                    participant=Participant.AKA.value,
                    color="red",
                    title="AKA",
                ),
                rx.vstack(
                    timer(),
                    rx.button(
                        "Undo",
                        on_click=KumiteMatchState.undo_last_action,
                    ),
                    align="center",
                ),
                _participant_panel(
                    participant=Participant.AO.value,
                    color="blue",
                    title="AO",
                ),
            ),
            spacing="4",
        )
    )
