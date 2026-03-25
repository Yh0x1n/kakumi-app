"""
KAKUMI
Módulo de componentes de formularios y tablas de registros
(Atletas, Categorías y Árbitros)
"""

import reflex as rx

from ..models.athlete_model import Athlete  # noqa [0401]
from ..models.referee_model import Referee  # noqa [0401]
from ..models.tournament_model import (  # noqa [0401]
    KataCategory,
    KumiteCategory,
    Tournament,
)


def athletes_registry() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.vstack(),
        )
    )


def category_registry() -> rx.Component:
    pass


def referee_registry() -> rx.Component:
    pass
