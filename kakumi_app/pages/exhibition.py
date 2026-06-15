"""
KAKUMI
Módulo de página de exhibición
(modo de sistema de puntaje sin registro de torneo).
"""

# Importaciones
import reflex as rx

from ..components.kata_scoreboard import kata_scoreboard
from ..components.kumite_scoreboard import kumite_scoreboard
from ..components.registry_crud import registry_page_shell
from ..states.kata_match_state import KataMatchState
from ..states.kumite_match_state import KumiteMatchState

from kakumi_app.styles.tokens import (
    BRAND_RED_HOVER,
    BRAND_RED_HOVER_LIGHT,
    TEXT_WHITE,
)


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

# ── Constantes (mismas que registries_items) ─────
_EXH_ICON_SIZE = "90px"
_EXH_CARD_SIZE = "40vh"
_EXH_CARD_PADDING = "5rem"
_EXH_CARD_RADIUS = "0.5em"
_EXH_CARD_STYLE = {
    "cursor": "pointer",
    "bg": BRAND_RED_HOVER,
    "border_radius": _EXH_CARD_RADIUS,
    "_hover": {
        "bg": BRAND_RED_HOVER_LIGHT,
        "color": TEXT_WHITE,
        "transition": "0.5s ease",
    },
}


def _exh_icon(icon_path: str) -> rx.Component:
    """Ícono inline con filtro blanco, como registries."""
    return rx.image(
        icon_path,
        style={"filter": "invert(1)", "color": TEXT_WHITE},
        width=_EXH_ICON_SIZE,
        height=_EXH_ICON_SIZE,
    )


def _exh_card(text: str, icon_path: str, href: str) -> rx.Component:
    """Card de exhibición, misma estructura que registries."""
    return rx.link(
        rx.vstack(
            _exh_icon(icon_path),
            rx.text(text, font_size="20px", color=TEXT_WHITE, font_weight="bold"),
            width="100%",
            height="100%",
            align="center",
            justify="center",
            padding=_EXH_CARD_PADDING,
            style=_EXH_CARD_STYLE,
        ),
        href=href,
        underline="none",
        width=_EXH_CARD_SIZE,
        height=_EXH_CARD_SIZE,
    )


# Menú de exhibición
def exhibition() -> rx.Component:
    body = rx.vstack(
        rx.vstack(
            rx.heading("Exhibición", size="8"),
            rx.text("Aquí se mostrarán los detalles del modo de exhibición."),
            spacing="1",
            align="start",
            width="100%",
        ),
        rx.center(
            rx.hstack(
                _exh_card("Kata", "icons/kata.png", "/exhibition/kata_system"),
                _exh_card("Kumite", "icons/kumite.png", "/exhibition/kumite_system"),
                spacing="5",
                justify="center",
            ),
            width="100%",
        ),
        spacing="4",
        width="100%",
    )
    return registry_page_shell(body=body)
