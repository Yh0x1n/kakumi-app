"""Registry pages for athletes, referees and tournaments."""

from __future__ import annotations

from typing import Any

import reflex as rx

from kakumi_app.components.registries_items import reg_items
from kakumi_app.components.registry_crud import (
    registry_actions_header,
    registry_empty_state,
    registry_error,
    registry_import_panel,
    registry_page_shell,
    registry_pagination_footer,
    registry_table,
    registry_table_card,
    registry_table_filters,
)
from kakumi_app.states.athlete_state import AthleteState
from kakumi_app.utils import BELT_RANKS
from kakumi_app.states.referee_state import RefereeState
from kakumi_app.components.date_calendar import date_calendar_popover
from kakumi_app.states.tournament_crud_state import TournamentCrudState


def _registry_form_heading(title: rx.Var | str) -> rx.Component:
    """Render shared form heading for registry modals/cards."""
    return rx.heading(title, size="6")


def registries() -> rx.Component:
    """Root registries launcher page."""
    return registry_page_shell(
        body=rx.vstack(
            rx.vstack(
                rx.heading("Registros", size="8"),
                rx.text(
                    "Selecciona un módulo para gestionar atletas, árbitros y torneos.",
                ),
                spacing="1",
                align="start",
                width="100%",
            ),
            rx.center(reg_items(), width="100%"),
            width="100%",
            spacing="4",
        )
    )


def _athlete_form() -> rx.Component:
    """Render create/edit athlete form."""
    state = AthleteState

    def row(left: rx.Component, right: rx.Component) -> rx.Component:
        # 1 columna en mobile/tablet, 2 columnas en desktop
        return rx.flex(
            rx.box(left, width=["100%", "100%", "75%"]),
            rx.box(right, width=["100%", "100%", "75%"]),
            width="100%",
            spacing="2",
            flex_direction=["column", "column", "row"],
        )

    return rx.box(
        rx.form(
            rx.flex(
                _registry_form_heading(
                    rx.cond(state.is_editing, "Editar Atleta", "Nuevo Atleta"),
                ),
                row(
                    rx.vstack(
                        rx.heading("Nombre *", size="3"),
                        rx.input(
                            placeholder="Nombre *",
                            value=state.name,
                            on_change=state.set_name,
                            border="1px solid white",
                        ),
                    ),
                    rx.vstack(
                        rx.heading("Email", size="3"),
                        rx.input(
                            placeholder="Email",
                            value=state.email,
                            on_change=state.set_email,
                            type="email",
                            border="1px solid white",
                        ),
                    ),
                ),
                row(
                    rx.vstack(
                        rx.heading("Edad", size="3"),
                        rx.input(
                            placeholder="Edad *",
                            value=state.age,
                            on_change=state.set_age,
                            type="number",
                            border="1px solid white",
                        ),
                    ),
                    rx.vstack(
                        rx.heading("Género", size="3"),
                        rx.select(
                            ["MASCULINO", "FEMENINO"],
                            value=state.gender,
                            on_change=state.set_gender,
                            style={
                                "border": "1px solid white",
                                "background_color": "black",
                            },
                        ),
                    ),
                ),
                row(
                    rx.vstack(
                        rx.heading("Peso (kg)", size="3"),
                        rx.input(
                            placeholder="Peso (kg)",
                            value=state.weight_kg,
                            on_change=state.set_weight_kg,
                            type="number",
                            border="1px solid white",
                        ),
                    ),
                    rx.vstack(
                        rx.heading("Grado", size="3"),
                        rx.select(
                            BELT_RANKS,
                            value=state.belt_rank,
                            on_change=state.set_belt_rank,
                            placeholder="Selecciona un grado",
                            style={
                                "border": "1px solid white",
                                "background_color": "white",
                            },
                        ),
                    ),
                ),
                row(
                    rx.vstack(
                        rx.heading("Dojo", size="3"),
                        rx.input(
                            placeholder="Dojo",
                            value=state.dojo,
                            on_change=state.set_dojo,
                            border="1px solid white",
                        ),
                    ),
                    rx.vstack(
                        rx.heading("Nacionalidad (ISO 3 letras)", size="3"),
                        rx.input(
                            placeholder="Nacionalidad (ISO 3 letras)",
                            value=state.nationality,
                            on_change=state.set_nationality,
                            max_length=3,
                            border="1px solid white",
                        ),
                    ),
                ),
                # Fila final
                rx.flex(
                    rx.box(
                        rx.vstack(
                            rx.heading("Licencia", size="3"),
                            rx.input(
                                placeholder="Licencia",
                                value=state.license_number,
                                on_change=state.set_license_number,
                                border="1px solid white",
                            ),
                        ),
                        width=["100%", "100%", "50%"],
                    ),
                    rx.box(
                        rx.checkbox(
                            rx.text("Activo"),
                            checked=state.is_active,
                            on_change=state.set_is_active,
                        ),
                        width=["100%", "100%", "50%"],
                    ),
                    width="100%",
                    spacing="3",
                    flex_direction=["column", "column", "row"],
                ),
                rx.hstack(
                    rx.button("Guardar", type="submit", color_scheme="green"),
                    rx.button("Cancelar", on_click=state.cancel_form),
                    spacing="3",
                ),
                width="100%",
                spacing="3",
                flex_direction="column",
            ),
            on_submit=state.save_athlete,
        ),
        width="100%",
    )


def _referee_form() -> rx.Component:
    """Render create/edit referee form."""
    state = RefereeState

    def row(left: rx.Component, right: rx.Component) -> rx.Component:
        # 1 columna en mobile/tablet, 2 columnas en desktop
        return rx.flex(
            rx.box(left, width=["100%", "100%", "50%"]),
            rx.box(right, width=["100%", "100%", "50%"]),
            width="100%",
            spacing="3",
            flex_direction=["column", "column", "row"],
        )

    return rx.box(
        rx.form(
            rx.flex(
                _registry_form_heading(
                    rx.cond(state.is_editing, "Editar Árbitro", "Nuevo Árbitro")
                ),
                row(
                    rx.vstack(
                        rx.heading("Nombre *", size="3"),
                        rx.input(
                            placeholder="Nombre *",
                            value=state.name,
                            on_change=state.set_name,
                            border="1px solid white",
                        ),
                    ),
                    rx.vstack(
                        rx.heading("Licencia *", size="3"),
                        rx.select(
                            state.license_number_options,
                            value=state.license_number,
                            on_change=state.set_license_number,
                            placeholder="Selecciona o escribe licencia",
                            style={
                                "border": "1px solid white",
                                "background_color": "white",
                            },
                        ),
                    ),
                ),
                row(
                    rx.vstack(
                        rx.heading("Nivel de licencia", size="3"),
                        rx.select(
                            ["NACIONAL", "INTERNACIONAL"],
                            value=state.license_level,
                            on_change=state.set_license_level,
                            style={
                                "border": "1px solid white",
                                "background_color": "white",
                            },
                        ),
                    ),
                    rx.vstack(
                        rx.heading("Rol", size="3"),
                        rx.select(
                            [
                                "ÁRBITRO",
                                "JUEZ",
                                "OFICIAL DE MESA",
                                "SUPERVISOR (KANSA)",
                            ],
                            value=state.role,
                            on_change=state.set_role,
                            style={
                                "border": "1px solid white",
                                "background_color": "white",
                            },
                        ),
                    ),
                ),
                row(
                    rx.vstack(
                        rx.heading("Certificación tatami (JSON)", size="3"),
                        rx.input(
                            placeholder="Certificación tatami (JSON)",
                            value=state.tatami_certified,
                            on_change=state.set_tatami_certified,
                            border="1px solid white",
                        ),
                    ),
                    rx.vstack(
                        rx.heading("Dojo", size="3"),
                        rx.input(
                            placeholder="Dojo",
                            value=state.dojo,
                            on_change=state.set_dojo,
                            border="1px solid white",
                        ),
                    ),
                ),
                row(
                    rx.vstack(
                        rx.heading("Email", size="3"),
                        rx.input(
                            placeholder="Email",
                            value=state.email,
                            on_change=state.set_email,
                            type="email",
                            border="1px solid white",
                        ),
                    ),
                    rx.vstack(
                        rx.heading("Teléfono", size="3"),
                        rx.input(
                            placeholder="Teléfono",
                            value=state.phone,
                            on_change=state.set_phone,
                            border="1px solid white",
                        ),
                    ),
                ),
                rx.flex(
                    rx.box(
                        rx.checkbox(
                            rx.text("Disponible"),
                            checked=state.is_available,
                            on_change=state.set_is_available,
                        ),
                        width=["100%", "100%", "50%"],
                    ),
                    rx.box(width=["100%", "100%", "50%"]),
                    width="100%",
                    spacing="3",
                    flex_direction=["column", "column", "row"],
                ),
                rx.hstack(
                    rx.button("Guardar", type="submit", color_scheme="green"),
                    rx.button("Cancelar", on_click=state.cancel_form),
                    spacing="3",
                ),
                width="100%",
                spacing="3",
                flex_direction="column",
            ),
            on_submit=state.save_referee,
        ),
        width="100%",
    )


def _tournament_form(
    on_submit_override: Any | None = None,
    on_cancel_override: Any | None = None,
) -> rx.Component:
    """Render create/edit tournament form.

    Args:
        on_submit_override: Optional handler to replace state.save_tournament.
            Used by TournamentState bridge to advance step after save.
        on_cancel_override: Optional handler to replace state.cancel_form.
            Used by TournamentState bridge to cancel the create flow.
    """
    state = TournamentCrudState
    submit_handler = on_submit_override or state.save_tournament
    cancel_handler = on_cancel_override or state.cancel_form

    def row(left: rx.Component, right: rx.Component) -> rx.Component:
        # 1 columna en mobile/tablet, 2 columnas en desktop
        return rx.flex(
            rx.box(left, width=["100%", "100%", "50%"]),
            rx.box(right, width=["100%", "100%", "50%"]),
            width="100%",
            spacing="3",
            flex_direction=["column", "column", "row"],
        )

    return rx.box(
        rx.form(
            rx.flex(
                _registry_form_heading(
                    rx.cond(state.is_editing, "Editar Torneo", "Nuevo Torneo")
                ),
                row(
                    rx.vstack(
                        rx.heading("Nombre *", size="3"),
                        rx.input(
                            placeholder="Nombre *",
                            value=state.name,
                            on_change=state.set_name,
                            border="1px solid white",
                        ),
                    ),
                    rx.vstack(
                        rx.heading("Sede *", size="3"),
                        rx.input(
                            placeholder="Sede *",
                            value=state.venue,
                            on_change=state.set_venue,
                            border="1px solid white",
                        ),
                    ),
                ),
                row(
                    rx.vstack(
                        rx.heading("Inicio (DD/MM/AAAA)", size="3"),
                        date_calendar_popover(
                            value=state.start_date,
                            on_change=state.set_start_date,
                            target="start",
                        ),
                    ),
                    rx.vstack(
                        rx.heading("Fin (DD/MM/AAAA)", size="3"),
                        date_calendar_popover(
                            value=state.end_date,
                            on_change=state.set_end_date,
                            target="end",
                        ),
                    ),
                ),
                rx.flex(
                    rx.box(
                        rx.vstack(
                            rx.heading("Tatamis", size="3"),
                            rx.input(
                                placeholder="Tatamis",
                                value=state.tatami_count,
                                on_change=state.set_tatami_count,
                                type="number",
                                border="1px solid white",
                            ),
                        ),
                        width=["100%", "100%", "50%"],
                    ),
                    rx.box(width=["100%", "100%", "50%"]),
                    width="100%",
                    spacing="3",
                    flex_direction=["column", "column", "row"],
                ),
                rx.flex(
                    rx.box(
                        rx.vstack(
                            rx.heading("ID creador", size="3"),
                            rx.input(
                                placeholder="ID creador",
                                value=state.created_by_id,
                                on_change=state.set_created_by_id,
                                border="1px solid white",
                            ),
                        ),
                        width=["100%", "100%", "50%"],
                    ),
                    rx.box(width=["100%", "100%", "50%"]),
                    width="100%",
                    spacing="3",
                    flex_direction=["column", "column", "row"],
                ),
                rx.hstack(
                    rx.button("Guardar", type="submit", color_scheme="green"),
                    rx.button("Cancelar", on_click=cancel_handler),
                    spacing="3",
                ),
                width="100%",
                spacing="3",
                flex_direction="column",
            ),
            on_submit=submit_handler,
        ),
        width="100%",
    )


def _athletes_card() -> rx.Component:
    """Render athletes table card."""
    state = AthleteState
    return registry_table_card(
        filters=registry_table_filters(
            search_placeholder="Buscar por nombre, dojo o grado...",
            on_search_change=state.set_search_query,
            on_search_click=state.filter_athletes,
            result_label="Atletas registrados",
        ),
        table=registry_table(
            headers=["Nombre", "Email", "Dojo", "Estado", "Acciones"],
            rows_var=state.athletes,
            row_renderer=lambda athlete: rx.table.row(
                rx.table.cell(athlete["name"]),
                rx.table.cell(rx.cond(athlete["email"], athlete["email"], "-")),
                rx.table.cell(rx.cond(athlete["dojo"], athlete["dojo"], "-")),
                rx.table.cell(
                    rx.cond(athlete["is_active"], "Activo", "Inactivo"),
                ),
                rx.table.cell(
                    rx.hstack(
                        rx.button(
                            "Editar",
                            size="2",
                            on_click=lambda event: state.set_form_values(
                                event, athlete
                            ),
                        ),
                        rx.button(
                            "Eliminar",
                            size="2",
                            color_scheme="red",
                            on_click=lambda: state.delete_athlete(athlete["id"]),
                        ),
                    )
                ),
            ),
            empty_state=registry_empty_state(
                icon="🥋",
                title="No hay atletas registrados",
                subtitle=(
                    "Comienza añadiendo un atleta manualmente o importando una lista"
                ),
                cta_label="Añadir Primer Atleta",
                on_cta_click=state.set_form_values,
            ),
        ),
        footer=registry_pagination_footer(summary_label="Mostrando atletas"),
    )


def _athletes_import_panel() -> rx.Component:
    """Render athlete import panel with upload flow."""
    state = AthleteState
    upload_id = "athletes_registry_upload"
    return registry_import_panel(
        upload_id=upload_id,
        selected_file_name=state.import_file_name,
        on_upload_click=state.handle_import_upload(
            rx.upload_files(upload_id=upload_id)
        ),
        on_cancel_click=[state.close_import_panel, rx.clear_selected_files(upload_id)],
    )


def _referees_card() -> rx.Component:
    """Render referees table card."""
    state = RefereeState
    return registry_table_card(
        filters=registry_table_filters(
            search_placeholder="Buscar por nombre, licencia o dojo...",
            on_search_change=state.set_search_query,
            on_search_click=state.filter_referees,
            result_label="Árbitros registrados",
        ),
        table=registry_table(
            headers=["Nombre", "Licencia", "Dojo", "Estado", "Acciones"],
            rows_var=state.referees,
            row_renderer=lambda referee: rx.table.row(
                rx.table.cell(referee["name"]),
                rx.table.cell(referee["license_number"]),
                rx.table.cell(rx.cond(referee["dojo"], referee["dojo"], "-")),
                rx.table.cell(
                    rx.cond(referee["is_available"], "Disponible", "No disponible"),
                ),
                rx.table.cell(
                    rx.hstack(
                        rx.button(
                            "Editar",
                            size="2",
                            on_click=lambda event: state.set_form_values(
                                event, referee
                            ),
                        ),
                        rx.button(
                            "Eliminar",
                            size="2",
                            color_scheme="red",
                            on_click=lambda: state.delete_referee(referee["id"]),
                        ),
                    )
                ),
            ),
            empty_state=registry_empty_state(
                icon="🧑‍⚖️",
                title="No hay árbitros registrados",
                subtitle=(
                    "Importa una lista de árbitros o carga el primero de forma manual"
                ),
                cta_label="Añadir Primer Árbitro",
                on_cta_click=state.set_form_values,
            ),
        ),
        footer=registry_pagination_footer(summary_label="Mostrando árbitros"),
    )


def _referees_import_panel() -> rx.Component:
    """Render referee import panel with upload flow."""
    state = RefereeState
    upload_id = "referees_registry_upload"
    return registry_import_panel(
        upload_id=upload_id,
        selected_file_name=state.import_file_name,
        on_upload_click=state.handle_import_upload(
            rx.upload_files(upload_id=upload_id)
        ),
        on_cancel_click=[state.close_import_panel, rx.clear_selected_files(upload_id)],
    )


def _tournaments_card() -> rx.Component:
    """Render tournaments table card."""
    state = TournamentCrudState
    return registry_table_card(
        filters=registry_table_filters(
            search_placeholder="Buscar torneos...",
            on_search_change=state.set_search_query,
            on_search_click=state.filter_tournaments,
            result_label="Torneos registrados",
        ),
        table=registry_table(
            headers=["Nombre", "Sede", "Estado", "Inicio", "Fin", "Acciones"],
            rows_var=state.tournaments,
            row_renderer=lambda tournament: rx.table.row(
                rx.table.cell(tournament["name"]),
                rx.table.cell(tournament["venue"]),
                rx.table.cell(tournament["status"]),
                rx.table.cell(tournament["start_date_display"]),
                rx.table.cell(tournament["end_date_display"]),
                rx.table.cell(
                    rx.hstack(
                        rx.button(
                            "Editar",
                            size="2",
                            on_click=lambda event: state.set_form_values(
                                event, tournament
                            ),
                        ),
                        rx.button(
                            "Eliminar",
                            size="2",
                            color_scheme="red",
                            on_click=lambda: state.delete_tournament(tournament["id"]),
                        ),
                    )
                ),
            ),
            empty_state=registry_empty_state(
                icon="🏆",
                title="No hay torneos registrados",
                subtitle="Crea un torneo para comenzar a gestionar la competencia",
                cta_label="Crear Primer Torneo",
                on_cta_click=state.set_form_values,
            ),
        ),
        footer=registry_pagination_footer(summary_label="Mostrando torneos"),
    )


@rx.page(route="/registries/athletes", on_load=AthleteState.initialize_registry_view)
def athletes() -> rx.Component:
    """Athletes CRUD page."""
    state = AthleteState
    body = rx.vstack(
        registry_actions_header(
            title="Gestión de Atletas",
            subtitle="Directorio principal de competidores registrados.",
            help_text="Importa o exporta plantillas .xlsx con encabezados en español.",
            add_label="Añadir Atleta",
            on_add_click=state.set_form_values,
            import_label="Importar .xlsx",
            export_label="Exportar .xlsx",
            on_import_click=state.import_athletes,
            on_export_click=state.export_athletes,
        ),
        registry_error(state.error_message),
        rx.cond(
            state.show_form,
            _athlete_form(),
            rx.cond(
                state.show_import_panel, _athletes_import_panel(), _athletes_card()
            ),
        ),
        spacing="4",
        width="100%",
    )
    return registry_page_shell(body=body)


@rx.page(route="/registries/referees", on_load=RefereeState.initialize_registry_view)
def referees() -> rx.Component:
    """Referees CRUD page."""
    state = RefereeState
    body = rx.vstack(
        registry_actions_header(
            title="Gestión de Árbitros",
            subtitle="Directorio y control de licencias oficiales.",
            help_text="Importa o exporta plantillas .xlsx con encabezados en español.",
            add_label="Añadir Árbitro",
            on_add_click=state.set_form_values,
            import_label="Importar .xlsx",
            export_label="Exportar .xlsx",
            on_import_click=state.import_referees,
            on_export_click=state.export_referees,
        ),
        registry_error(state.error_message),
        rx.cond(
            state.show_form,
            _referee_form(),
            rx.cond(
                state.show_import_panel,
                _referees_import_panel(),
                _referees_card(),
            ),
        ),
        spacing="4",
        width="100%",
    )
    return registry_page_shell(body=body)


@rx.page(
    route="/registries/tournaments",
    on_load=TournamentCrudState.initialize_registry_view,
)
def tournaments() -> rx.Component:
    """Tournaments CRUD page."""
    state = TournamentCrudState
    body = rx.vstack(
        registry_actions_header(
            title="Gestión de Torneos",
            subtitle="Administra y supervisa los eventos de competición.",
            add_label="Nuevo Torneo",
            on_add_click=state.set_form_values,
        ),
        registry_error(state.error_message),
        rx.cond(state.show_form, _tournament_form(), _tournaments_card()),
        spacing="4",
        width="100%",
    )
    return registry_page_shell(body=body)
