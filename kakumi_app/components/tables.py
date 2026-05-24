"""
KAKUMI
Módulo de tablas para registros de atletas, categorías y árbitros.
"""

import reflex as rx

from kakumi_app.styles.tokens import TEXT_TERTIARY


def athletes_table() -> rx.Component:
    """Placeholder for athletes table component."""
    return rx.box(
        rx.text("Tabla de atletas - no implementado", color=TEXT_TERTIARY),
    )
