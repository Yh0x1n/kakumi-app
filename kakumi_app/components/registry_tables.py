"""
KAKUMI
Módulo de componentes de formularios y tablas de registros
(Atletas, Categorías y Árbitros)
"""

import reflex as rx


def athletes_registry() -> rx.Component:
    """Placeholder for athletes registry component."""
    return rx.box(
        rx.text("Registro de atletas - no implementado", color="gray"),
    )


def category_registry() -> rx.Component:
    """Placeholder for category registry component."""
    return rx.box(
        rx.text("Registro de categorías - no implementado", color="gray"),
    )


def referee_registry() -> rx.Component:
    """Placeholder for referee registry component."""
    return rx.box(
        rx.text("Registro de árbitros - no implementado", color="gray"),
    )
