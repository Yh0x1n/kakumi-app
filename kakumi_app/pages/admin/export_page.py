"""
Export Results Page
Allows exporting tournament results in JSON/CSV format.
"""

import reflex as rx
from kakumi_app.states.export_state import ExportState
from kakumi_app.components.sidebar import sidebar


def export_form() -> rx.Component:
    """Form for exporting tournament results."""
    state = ExportState

    return rx.vstack(
        rx.heading(
            "Exportar Resultados de Torneo", font_size="2xl", margin_bottom="1em"
        ),
        rx.text(
            "Selecciona un torneo y formato para exportar resultados.",
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
        rx.form(
            rx.vstack(
                rx.select(
                    [f"{t.id}: {t.name}" for t in state.tournaments],
                    value=state.selected_tournament_id,
                    on_change=state.set_selected_tournament_id,
                    width="100%",
                    placeholder="Seleccionar torneo *",
                ),
                rx.hstack(
                    rx.radio(
                        "JSON",
                        value="json",
                        checked=state.export_format == "json",
                        on_change=state.set_export_format,
                    ),
                    rx.radio(
                        "CSV",
                        value="csv",
                        checked=state.export_format == "csv",
                        on_change=state.set_export_format,
                    ),
                    spacing="2em",
                    margin_y="1em",
                ),
                rx.button(
                    "Exportar",
                    type="submit",
                    color_scheme="green",
                    loading=state.is_exporting,
                    disabled=state.is_exporting,
                    width="100%",
                ),
                spacing="1em",
            ),
            on_submit=state.export_tournament_results,
        ),
        rx.cond(
            state.export_content,
            rx.box(
                rx.vstack(
                    rx.heading(f"Archivo: {state.export_filename}", font_size="lg"),
                    rx.text(
                        "Contenido generado:", font_weight="bold", margin_top="1em"
                    ),
                    rx.box(
                        rx.text(
                            state.export_content[:500] + "..."
                            if len(state.export_content) > 500
                            else state.export_content,
                            font_family="monospace",
                            font_size="sm",
                            white_space="pre-wrap",
                            max_height="300px",
                            overflow_y="auto",
                            border="1px solid #eee",
                            padding="1em",
                            border_radius="4px",
                            background_color="#f9f9f9",
                        ),
                    ),
                    rx.hstack(
                        rx.button(
                            "Copiar al Portapapeles",
                            on_click=rx.set_clipboard(state.export_content),
                            color_scheme="blue",
                        ),
                        rx.button(
                            "Nueva Exportación",
                            on_click=state.clear_export,
                            color_scheme="gray",
                        ),
                        spacing="1em",
                        margin_top="1em",
                    ),
                ),
                border="1px solid #ddd",
                padding="1em",
                border_radius="8px",
                margin_top="2em",
            ),
        ),
        rx.link(
            rx.button("Volver a Resultados", color_scheme="gray"),
            href="/results",
            margin_top="2em",
        ),
        width="100%",
        max_width="800px",
        margin="0 auto",
        padding="2em",
    )


def export_page() -> rx.Component:
    """Main export page layout."""
    state = ExportState

    # Load tournaments on page load
    state.load_tournaments()

    return rx.box(
        rx.vstack(
            rx.hstack(
                sidebar(),
                rx.vstack(
                    export_form(),
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


@rx.page(route="/admin/export")
def export_results() -> rx.Component:
    """Route for export results page."""
    return export_page()
