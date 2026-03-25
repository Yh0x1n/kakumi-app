"""
KAKUMI
Módulo de página de exhibición
(modo de sistema de puntaje sin registro de torneo).
"""

# Importaciones
import reflex as rx

from ..components.sidebar import sidebar
from ..components.timer import timer


# Subpágina del temporizador (Aquí irá todo el sistema de kumite)
@rx.page(route="/exhibition/kumite_system")
def kumite_system() -> rx.Component:
    return rx.box(rx.vstack(timer()))


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
