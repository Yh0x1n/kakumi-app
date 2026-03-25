"""
KAKUMI
Módulo de página de torneo.
"""

# Importaciones
import reflex as rx

from ..components.sidebar import sidebar

# from ..models import Tournament


def tournament() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                sidebar(),
                rx.vstack(
                    rx.heading(
                        "Torneo",
                        font_size=50,
                        align="left",
                        padding_y="0.5em",
                        color="black",
                        font_weight="bold",
                    ),
                    rx.text(
                        "Aquí se mostrarán los detalles del torneo.",
                        font_size=16,
                        align="left",
                        color="black",
                    ),
                ),
            ),
            background_color="white",
        ),
        width="100%",
        background_color="white",
        height="100vh",
    )
