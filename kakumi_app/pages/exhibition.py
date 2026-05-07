"""
KAKUMI
Módulo de página de exhibición
(modo de sistema de puntaje sin registro de torneo).
"""

# Importaciones
import reflex as rx

from ..components.kumite_scoreboard import kumite_scoreboard
from ..components.sidebar import sidebar
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
                        color="black",
                        font_weight="bold",
                    ),
                    rx.text(
                        "Aquí se mostrarán los detalles del modo de exhibición.",
                        font_size=16,
                        align="left",
                        color="black",
                    ),
                    rx.link(rx.button("Ir a Kumite"), href="/exhibition/kumite_system"),
                ),
            ),
            background_color="white",
        ),
        width="100%",
        background_color="white",
        height="100vh",
    )
