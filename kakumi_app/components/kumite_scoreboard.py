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
    score_color = rx.cond(
        is_aka,
        KumiteMatchState.aka_score_color,
        KumiteMatchState.ao_score_color,
    )

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
                color="white",
            ),
            rx.button(
                "Revocar SENSHU",
                variant="outline",
                on_click=KumiteMatchState.revoke_manual_senshu(participant=participant),
                color="white",
            ),
            spacing="2",
        ),
        rx.heading(score, as_="div", size="9", color=score_color),
        rx.hstack(
            rx.button(
                "YUKO",
                on_click=KumiteMatchState.apply_score(
                    participant=participant,
                    score_type=ScoreType.YUKO.value,
                    applied_by_id=1,
                ),
                bg="gray",
            ),
            rx.button(
                "WAZA-ARI",
                on_click=KumiteMatchState.apply_score(
                    participant=participant,
                    score_type=ScoreType.WAZA_ARI.value,
                    applied_by_id=1,
                ),
                bg="gray",
            ),
            rx.button(
                "IPPON",
                on_click=KumiteMatchState.apply_score(
                    participant=participant,
                    score_type=ScoreType.IPPON.value,
                    applied_by_id=1,
                ),
                bg="gray",
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
        rx.hstack(
            rx.button(
                "Penalización",
                bg="yellow",
                color="black",
                on_click=KumiteMatchState.apply_penalty_cumulative(participant),
            ),
            rx.button(
                "Descalificación",
                bg="crimson",
                fg="white",
                on_click=KumiteMatchState.open_disqualification_dialog(
                    participant=participant,
                ),
            ),
            spacing="2",
        ),
        bg=color,
        width="50vh",
        align="center",
        padding="3",
        border_radius="5px",
        padding_y="10px",
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
                rx.box(
                    _participant_panel(
                        participant=Participant.AKA.value,
                        color="red",
                        title="AKA",
                    ),
                    display="flex",
                    justify_content="center",
                ),
                rx.box(
                    rx.vstack(
                        timer(),
                        rx.button(
                            "Deshacer",
                            on_click=KumiteMatchState.undo_last_action,
                        ),
                        rx.cond(
                            KumiteMatchState.is_exhibition_mode,
                            rx.button(
                                "Reiniciar puntos",
                                on_click=KumiteMatchState.reset_points,
                                variant="outline",
                            ),
                            rx.fragment(),
                        ),
                        align="center",
                        width="100%",
                    ),
                    max_width="100%",
                    display="flex",
                    justify_content="center",
                    align_items="center",
                    flex_shrink="0",
                ),
                rx.box(
                    _participant_panel(
                        participant=Participant.AO.value,
                        color="blue",
                        title="AO",
                    ),
                    display="flex",
                    justify_content="center",
                ),
                align="start",
                justify="center",
                width="100%",
            ),
            rx.cond(
                KumiteMatchState.disqualification_dialog_open,
                rx.dialog.root(
                    rx.dialog.content(
                        rx.dialog.title("Descalificación"),
                        rx.dialog.description(
                            "Seleccioná tipo de descalificación para finalizar combate"
                        ),
                        rx.hstack(
                            rx.button(
                                "SHIKKAKU",
                                color_scheme="red",
                                on_click=KumiteMatchState.apply_disqualification(
                                    "SHIKKAKU"
                                ),
                            ),
                            rx.button(
                                "KIKEN",
                                color_scheme="orange",
                                on_click=KumiteMatchState.apply_disqualification(
                                    "KIKEN"
                                ),
                            ),
                            spacing="2",
                        ),
                        rx.button(
                            "Cancelar",
                            on_click=KumiteMatchState.close_disqualification_dialog,
                            variant="soft",
                        ),
                    ),
                    open=KumiteMatchState.disqualification_dialog_open,
                ),
                rx.fragment(),
            ),
            rx.cond(
                KumiteMatchState.match_end_modal_open,
                rx.dialog.root(
                    rx.dialog.content(
                        rx.dialog.title("HANTEI"),
                        rx.dialog.description(KumiteMatchState.match_end_message),
                        rx.cond(
                            KumiteMatchState.hantei_required,
                            rx.hstack(
                                rx.button(
                                    "Gana AKA",
                                    on_click=KumiteMatchState.apply_hantei_decision(
                                        winner_participant=Participant.AKA.value,
                                    ),
                                ),
                                rx.button(
                                    "Gana AO",
                                    on_click=KumiteMatchState.apply_hantei_decision(
                                        winner_participant=Participant.AO.value,
                                    ),
                                ),
                                spacing="2",
                            ),
                            rx.button(
                                "Entendido",
                                on_click=KumiteMatchState.close_match_end_modal,
                                variant="soft",
                            ),
                        ),
                    ),
                    open=KumiteMatchState.match_end_modal_open,
                ),
                rx.fragment(),
            ),
            spacing="4",
            align="center",
        ),
    )
