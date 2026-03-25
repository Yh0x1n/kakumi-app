"""
+------------------------------------------------------+
+             Kakumi Tournament Manager                +
+       Web application for Karate-Do tournaments      +
+------------------------------------------------------+
+           Developed by Yhoxin Rossell                +
+           GitHub: @Yh0x1n                            +
+------------------------------------------------------+
"""

# Imports
import reflex as rx

from .components.sidebar import sidebar
from .models.athlete_model import Athlete  # noqa [F401]
from .models.referee_model import Referee  # noqa [F401]
from .models.tournament_model import (  # noqa [F401]
    KataCategory,
    KumiteCategory,
    Tournament,
)
from .pages.exhibition import exhibition
from .pages.registries import registries
from .pages.tournament import tournament


class State(rx.State):
    pass


def index() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                sidebar(),
                rx.heading(
                    "Welcome to Kakumi Tournament Manager!",
                    font_size=50,
                    align="left",
                    padding_y="0.5em",
                    color="black",
                    font_weight="bold",
                ),
                spacing="4",
            ),
        ),
        rx.center(
            rx.grid(
                rx.foreach(
                    rx.Var.range(4),
                    lambda i: rx.card(
                        rx.link(
                            rx.text(
                                f"Resultado {i + 1}",
                                weight="bold",
                                font_size="10",
                                color="black",
                            ),
                            underline="none",
                            height="100%",
                        ),
                        border_width="thick",
                        border_color="black",
                        border_radius="1em",
                        style={
                            "_hover": {
                                "background-color": "#e0e0e0",
                                "transition": "0.5s ease",
                            },
                        },
                    ),
                ),
                columns="2",
                spacing="4",
                width="50%",
                padding="0.5em",
            ),
        ),
        background_color="white",
        height="100vh",
    )


app = rx.App()
app.add_page(index, title="Kakumi Tournament Manager")
app.add_page(registries, title="Kakumi | Registros")
app.add_page(tournament, title="Kakumi | Torneo")
app.add_page(exhibition, title="Kakumi | Exhibición")
