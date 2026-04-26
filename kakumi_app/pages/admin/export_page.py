"""
Export Results Page
Allows exporting tournament results in JSON/CSV format.
"""

import reflex as rx

from kakumi_app.states.export_state import ExportState
from kakumi_app.components.sidebar import sidebar
from kakumi_app.styles.tokens import BG_CODE_PREVIEW, BORDER_LIGHT, BORDER_SUBTLE


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
        rx.form(
            rx.vstack(
                rx.select(
                    state.tournament_options,
                    value=state.selected_tournament_id,
                    on_change=state.set_selected_tournament_id,
                    width="100%",
                    placeholder="Seleccionar torneo *",
                ),
                rx.radio_group(
                    ["json", "csv"],
                    value=state.export_format,
                    on_change=state.set_export_format,
                    direction="row",
                    spacing="4",
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
                spacing="4",
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
                            state.export_preview,
                            font_family="monospace",
                            font_size="sm",
                            white_space="pre-wrap",
                            max_height="300px",
                            overflow_y="auto",
                            border=f"1px solid {BORDER_LIGHT}",
                            padding="1em",
                            border_radius="4px",
                            background_color=BG_CODE_PREVIEW,
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
                        spacing="4",
                        margin_top="1em",
                    ),
                ),
                border=f"1px solid {BORDER_SUBTLE}",
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


@rx.page(route="/admin/export", on_load=ExportState.load_tournaments)
def export_results() -> rx.Component:
    """Route for export results page."""
    return export_page()
