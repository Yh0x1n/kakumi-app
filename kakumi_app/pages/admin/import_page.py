"""Legacy admin import route redirected to shared registries flow."""

import reflex as rx


@rx.page(route="/admin/import", on_load=rx.redirect("/registries/athletes"))
def import_athletes() -> rx.Component:
    """Redirect deprecated admin import page to shared athlete registry import."""
    return rx.box(
        rx.vstack(
            rx.heading("Importación de registros", size="6"),
            rx.text(
                "Redirigiendo al flujo unificado de atletas (.xlsx).",
            ),
            spacing="2",
            align="start",
        ),
        width="100%",
        min_height="40vh",
        padding="2em",
    )
