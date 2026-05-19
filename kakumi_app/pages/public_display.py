"""Public read-only page for secondary display snapshots."""

from __future__ import annotations

import reflex as rx

from kakumi_app.components.public_kata_display import public_kata_display
from kakumi_app.components.public_kumite_display import public_kumite_display
from kakumi_app.states.secondary_display_state import SecondaryDisplayState


def public_display_page() -> rx.Component:
    """Render projector-ready read-only scoreboard by display key."""
    return rx.box(
        rx.cond(
            SecondaryDisplayState.error_message != "",
            rx.center(
                rx.vstack(
                    rx.heading("Pantalla pública", size="8"),
                    rx.text("Solo lectura", size="4"),
                    rx.text(SecondaryDisplayState.error_message, color="red", size="5"),
                    spacing="3",
                    align="center",
                ),
                width="100vw",
                height="100vh",
                bg="black",
                color="white",
            ),
            rx.cond(
                SecondaryDisplayState.modality == "KATA",
                public_kata_display(),
                public_kumite_display(),
            ),
        ),
        rx.box(
            rx.hstack(
                rx.badge("Pantalla pública", color_scheme="green", size="2"),
                rx.badge("Solo lectura", color_scheme="gray", size="2"),
                rx.cond(
                    SecondaryDisplayState.is_stale,
                    rx.badge("Sincronización atrasada", color_scheme="orange", size="2"),
                    rx.badge("En vivo", color_scheme="green", size="2"),
                ),
                spacing="2",
            ),
            position="fixed",
            top="10px",
            right="10px",
            z_index="1000",
        ),
        width="100vw",
        height="100vh",
    )
