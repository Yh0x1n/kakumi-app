"""
Import Athletes Page
Allows uploading CSV/JSON files for bulk athlete import.
"""

import reflex as rx
from kakumi_app.states.import_state import ImportState
from kakumi_app.components.sidebar import sidebar


def import_form() -> rx.Component:
    """Form for uploading and importing athlete files."""
    state = ImportState

    return rx.vstack(
        rx.heading("Importar Atletas", font_size="2xl", margin_bottom="1em"),
        rx.text(
            "Sube un archivo CSV o JSON con los datos de los atletas.",
            font_size="md",
            color="gray",
            margin_bottom="2em",
        ),
        rx.cond(
            state.error_message,
            rx.callout(
                state.error_message,
                icon="alert-circle",
                color_scheme="red",
                margin_bottom="1em",
            ),
        ),
        rx.box(
            rx.upload(
                rx.vstack(
                    rx.icon(tag="upload", size=32),
                    rx.text("Arrastra y suelta el archivo aquí"),
                    rx.text("o haz clic para seleccionar"),
                    rx.text("Formatos: CSV, JSON", font_size="sm", color="gray"),
                ),
                id="upload",
                border="2px dashed #ccc",
                padding="2em",
                text_align="center",
                width="100%",
            ),
            margin_bottom="2em",
        ),
        rx.button(
            "Seleccionar Archivo",
            on_click=rx.upload(id="upload"),
            color_scheme="blue",
            margin_bottom="1em",
        ),
        rx.cond(
            state.file_name,
            rx.vstack(
                rx.text(f"Archivo: {state.file_name}", font_weight="bold"),
                rx.text(f"Tipo: {state.file_type.upper()}"),
                rx.button(
                    "Importar Atletas",
                    on_click=state.import_athletes,
                    color_scheme="green",
                    loading=state.is_importing,
                    disabled=state.is_importing,
                ),
                spacing="0.5em",
                margin_bottom="1em",
            ),
        ),
        rx.cond(
            state.show_results,
            rx.box(
                rx.vstack(
                    rx.heading("Resultados de Importación", font_size="xl"),
                    rx.hstack(
                        rx.badge(
                            f"Atletas importados: {state.success_count}",
                            color_scheme="green",
                            size="lg",
                        ),
                        rx.badge(
                            f"Errores: {state.error_count}",
                            color_scheme="red",
                            size="lg",
                        ),
                        spacing="1em",
                        margin_bottom="1em",
                    ),
                    rx.cond(
                        state.error_count > 0,
                        rx.vstack(
                            rx.heading("Detalles de Errores:", font_size="md"),
                            rx.foreach(
                                state.error_messages,
                                lambda error: rx.text(
                                    error, color="red", font_size="sm"
                                ),
                            ),
                            margin_bottom="1em",
                        ),
                    ),
                    rx.button(
                        "Nueva Importación",
                        on_click=state.reset_import,
                        color_scheme="blue",
                        margin_top="1em",
                    ),
                ),
                border="1px solid #ddd",
                padding="1em",
                border_radius="8px",
                margin_bottom="1em",
            ),
        ),
        rx.link(
            rx.button("Volver a Atletas", color_scheme="gray"),
            href="/registries/athletes",
            margin_top="2em",
        ),
        width="100%",
        max_width="800px",
        margin="0 auto",
        padding="2em",
    )


def import_page() -> rx.Component:
    """Main import page layout."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                sidebar(),
                rx.vstack(
                    import_form(),
                    width="100%",
                    padding="2em",
                ),
                width="100%",
            ),
            width="100%",
            background_color="white",
            min_height="100vh",
        ),
        width="100%",
    )


@rx.page(route="/admin/import")
def import_athletes() -> rx.Component:
    """Route for athlete import page."""
    return import_page()
