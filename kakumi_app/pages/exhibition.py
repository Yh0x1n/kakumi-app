"""
KAKUMI
Módulo de página de exhibición
(modo de sistema de puntaje sin registro de torneo).
"""

# Importaciones
import reflex as rx

from ..components.kata_scoreboard import kata_scoreboard
from ..components.kumite_scoreboard import kumite_scoreboard
from ..components.sidebar import sidebar
from ..states.kata_match_state import KataMatchState
from ..states.kumite_match_state import KumiteMatchState


# Subpágina del temporizador (Aquí irá todo el sistema de kumite)
@rx.page(
    route="/exhibition/kumite_system",
    on_load=KumiteMatchState.enable_exhibition_mode,
)
def kumite_system() -> rx.Component:
    return rx.center(
        rx.vstack(kumite_scoreboard()),
        align="center",
    )


@rx.page(
    route="/exhibition/kata_system",
    on_load=KataMatchState.enable_exhibition_mode,
)
def kata_system() -> rx.Component:
    return rx.center(
        rx.vstack(kata_scoreboard()),
        align="center",
    )


# Menú de exhibición
def exhibition() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                sidebar(),
                rx.vstack(
                    rx.heading(
                        "Exhibición",
                        font_size=50,
                        align="left",
                        padding_y="0.5em",
                        font_weight="bold",
                    ),
                    rx.text(
                        "Aquí se mostrarán los detalles del modo de exhibición.",
                        font_size=16,
                        align="left",
                    ),
                    rx.hstack(
                        rx.link(rx.button("Ir a Kata"), href="/exhibition/kata_system"),
                        rx.link(
                            rx.button("Ir a Kumite"), href="/exhibition/kumite_system"
                        ),
                    ),
                ),
            ),
        ),
        width="100%",
        height="100vh",
    )
