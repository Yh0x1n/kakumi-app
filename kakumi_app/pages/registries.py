"""KAKUMI
Módulo de páginas para registros de atletas, categorías y árbitros.
"""

# Importaciones
import reflex as rx

from ..components.registries_items import reg_items
from ..components.sidebar import sidebar

# from ..models import Athlete, Category, Referee, Tournament


# Subpágina de atletas
@rx.page(route="/registries/athletes")
def athletes() -> rx.Component:
    return rx.box(
        rx.text(
            "Aquí se mostrarán los registros de los atletas.",
            font_size=16,
            align="left",
            color="white",
        ),
        rx.link(rx.button("Volver a registros Atletas"), href="/registries"),
    )


# Subpágina de categorías
@rx.page(route="/registries/categories")
def categories() -> rx.Component:
    return rx.box(
        rx.text(
            "Aquí se mostrarán los registros de las categorías.",
            font_size=16,
            align="left",
            color="white",
        ),
        rx.link(rx.button("Volver a registros Categorias"), href="/registries"),
    )


# Subpágina de árbitros
@rx.page(route="/registries/referees")
def referees() -> rx.Component:
    return rx.box(
        rx.text(
            "Aquí se mostrarán los registros de los árbitros.",
            font_size=16,
            align="left",
            color="white",
        ),
        rx.link(rx.button("Volver a registros Árbitros"), href="/registries"),
    )


def registries() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                sidebar(),
                rx.vstack(
                    rx.heading(
                        "Registros",
                        font_size=50,
                        align="left",
                        padding_y="0.5em",
                        color="black",
                        font_weight="bold",
                    ),
                    rx.text(
                        "Elige el registro al que deseas acceder.",
                        font_size=16,
                        align="left",
                        color="black",
                    ),
                    rx.divider(border_color="black", margin_y="1em"),
                ),
                width="100%",
            ),
        ),
        rx.center(
            rx.box(
                reg_items(),
            ),
        ),
        width="100%",
        background_color="white",
        height="100vh",
    )
