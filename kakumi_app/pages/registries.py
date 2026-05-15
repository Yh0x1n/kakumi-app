"""Registry pages for athletes, referees and tournaments."""

from __future__ import annotations

import reflex as rx

from kakumi_app.components.registries_items import reg_items
from kakumi_app.components.registry_crud import (
    MUTED_TEXT,
    registry_actions_header,
    registry_empty_state,
    registry_error,
    registry_page_shell,
    registry_pagination_footer,
    registry_table,
    registry_table_card,
    registry_table_filters,
)
from kakumi_app.states.athlete_state import AthleteState
from kakumi_app.states.referee_state import RefereeState
from kakumi_app.states.tournament_crud_state import TournamentCrudState


def _registry_form_heading(title: rx.Var | str) -> rx.Component:
    """Render shared form heading for registry modals/cards."""
    return rx.heading(title, size="6", color="black")


def registries() -> rx.Component:
    """Root registries launcher page."""
    return registry_page_shell(
        body=rx.vstack(
            rx.vstack(
                rx.heading("Registros", size="8", color="black"),
                rx.text(
                    "Selecciona un módulo para gestionar atletas, árbitros y torneos.",
                    color=MUTED_TEXT,
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
                    rx.cond(state.is_editing, "Editar Atleta", "Nuevo Atleta"),
                ),
                row(
                    rx.vstack(
                        rx.heading("Nombre *", size="3", color="black"),
                        rx.input(
                            placeholder="Nombre *",
                            value=state.name,
                            on_change=state.set_name,
                            border="1px solid black",
                            background_color="white",
                            color="black",
                        ),
                    ),
                    rx.vstack(
                        rx.heading("Email", size="3", color="black"),
                        rx.input(
                            placeholder="Email",
                            value=state.email,
                            on_change=state.set_email,
                            type="email",
                            border="1px solid black",
                            background_color="white",
                            color="black",
                        ),
                    ),
                ),
                row(
                    rx.vstack(
                        rx.heading("Fecha Nac. (YYYY-MM-DD)", size="3", color="black"),
                        rx.input(
                            placeholder="Fecha Nac. (YYYY-MM-DD) *",
                            value=state.date_of_birth,
                            on_change=state.set_date_of_birth,
                            border="1px solid black",
                            background_color="white",
                            color="black",
                        ),
                    ),
                    rx.vstack(
                        rx.heading("Género", size="3", color="black"),
                        rx.select(
                            ["MASCULINO", "FEMENINO"],
                            value=state.gender,
                            on_change=state.set_gender,
                            style={
                                "border": "1px solid black",
                                "color": "black",
                                "background_color": "black",
                            },
                        ),
                    ),
                ),
                row(
                    rx.vstack(
                        rx.heading("Peso (kg)", size="3", color="black"),
                        rx.input(
                            placeholder="Peso (kg)",
                            value=state.weight_kg,
                            on_change=state.set_weight_kg,
                            type="number",
                            border="1px solid black",
                            background_color="white",
                            color="black",
                        ),
                    ),
                    rx.vstack(
                        rx.heading("Grado", size="3", color="black"),
                        rx.input(
                            placeholder="Grado",
                            value=state.belt_rank,
                            on_change=state.set_belt_rank,
                            border="1px solid black",
                            background_color="white",
                            color="black",
                        ),
                    ),
                ),
                row(
                    rx.vstack(
                        rx.heading("Dojo", size="3", color="black"),
                        rx.input(
                            placeholder="Dojo",
                            value=state.dojo,
                            on_change=state.set_dojo,
                            border="1px solid black",
                            background_color="white",
                            color="black",
                        ),
                    ),
                    rx.vstack(
                        rx.heading(
                            "Nacionalidad (ISO 3 letras)", size="3", color="black"
                        ),
                        rx.input(
                            placeholder="Nacionalidad (ISO 3 letras)",
                            value=state.nationality,
                            on_change=state.set_nationality,
                            max_length=3,
                            border="1px solid black",
                            background_color="white",
                            color="black",
                        ),
                    ),
                ),
                # Fila final (puedes dejarla a 1 columna si prefieres)
                rx.flex(
                    rx.box(
                        rx.vstack(
                            rx.heading("Licencia", size="3", color="black"),
                            rx.input(
                                placeholder="Licencia",
                                value=state.license_number,
                                on_change=state.set_license_number,
                                border="1px solid black",
                                background_color="white",
                                color="black",
                            ),
                        ),
                        width=["100%", "100%", "50%"],
                    ),
                    rx.box(
                        rx.checkbox(
                            rx.text("Activo", color="black"),
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
    return rx.box(
        rx.form(
            rx.vstack(
                _registry_form_heading(
                    rx.cond(state.is_editing, "Editar Árbitro", "Nuevo Árbitro")
                ),
                rx.hstack(
                    rx.vstack(
                        rx.input(
                            placeholder="Nombre *",
                            value=state.name,
                            on_change=state.set_name,
                        ),
                        rx.input(
                            placeholder="Licencia *",
                            value=state.license_number,
                            on_change=state.set_license_number,
                        ),
                        rx.select(
                            ["NATIONAL", "INTERNATIONAL"],
                            value=state.license_level,
                            on_change=state.set_license_level,
                        ),
                        rx.select(
                            ["REFEREE", "JUDGE", "TABLE_OFFICIAL", "SUPERVISOR"],
                            value=state.role,
                            on_change=state.set_role,
                        ),
                    ),
                    rx.vstack(
                        rx.input(
                            placeholder="Certificación tatami (JSON)",
                            value=state.tatami_certified,
                            on_change=state.set_tatami_certified,
                        ),
                        rx.checkbox(
                            "Disponible",
                            checked=state.is_available,
                            on_change=state.set_is_available,
                        ),
                        rx.input(
                            placeholder="Dojo",
                            value=state.dojo,
                            on_change=state.set_dojo,
                        ),
                        rx.input(
                            placeholder="Email",
                            value=state.email,
                            on_change=state.set_email,
                            type="email",
                        ),
                        rx.input(
                            placeholder="Teléfono",
                            value=state.phone,
                            on_change=state.set_phone,
                        ),
                        rx.hstack(
                            rx.button("Guardar", type="submit", color_scheme="green"),
                            rx.button("Cancelar", on_click=state.cancel_form),
                        ),
                    ),
                ),
                spacing="3",
            ),
            on_submit=state.save_referee,
        ),
        width="100%",
    )


def _tournament_form() -> rx.Component:
    """Render create/edit tournament form."""
    state = TournamentCrudState
    return rx.box(
        rx.form(
            rx.vstack(
                _registry_form_heading(
                    rx.cond(state.is_editing, "Editar Torneo", "Nuevo Torneo")
                ),
                rx.hstack(
                    rx.vstack(
                        rx.input(
                            placeholder="Nombre *",
                            value=state.name,
                            on_change=state.set_name,
                        ),
                        rx.input(
                            placeholder="Sede *",
                            value=state.venue,
                            on_change=state.set_venue,
                        ),
                        rx.input(
                            placeholder="Inicio (YYYY-MM-DD)",
                            value=state.start_date,
                            on_change=state.set_start_date,
                        ),
                        rx.input(
                            placeholder="Fin (YYYY-MM-DD)",
                            value=state.end_date,
                            on_change=state.set_end_date,
                        ),
                    ),
                    rx.vstack(
                        rx.input(
                            placeholder="Tatamis",
                            value=state.tatami_count,
                            on_change=state.set_tatami_count,
                            type="number",
                        ),
                        rx.select(
                            state.status_options,
                            value=state.status,
                            on_change=state.set_status,
                        ),
                        rx.input(
                            placeholder="ID creador",
                            value=state.created_by_id,
                            on_change=state.set_created_by_id,
                        ),
                        rx.hstack(
                            rx.button("Guardar", type="submit", color_scheme="green"),
                            rx.button("Cancelar", on_click=state.cancel_form),
                        ),
                    ),
                    spacing="3",
                ),
            ),
            on_submit=state.save_tournament,
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
                rx.table.cell(athlete["name"], color="black"),
                rx.table.cell(
                    rx.cond(athlete["email"], athlete["email"], "-"), color="black"
                ),
                rx.table.cell(
                    rx.cond(athlete["dojo"], athlete["dojo"], "-"), color="black"
                ),
                rx.table.cell(
                    rx.cond(athlete["is_active"], "Activo", "Inactivo"), color="black"
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
                rx.table.cell(referee["name"], color="black"),
                rx.table.cell(referee["license_number"], color="black"),
                rx.table.cell(
                    rx.cond(referee["dojo"], referee["dojo"], "-"), color="black"
                ),
                rx.table.cell(
                    rx.cond(referee["is_available"], "Disponible", "No disponible"),
                    color="black",
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
                    "Importá una lista de árbitros o cargá el primero de forma manual"
                ),
                cta_label="Añadir Primer Árbitro",
                on_cta_click=state.set_form_values,
            ),
        ),
        footer=registry_pagination_footer(summary_label="Mostrando árbitros"),
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
            headers=["Nombre", "Sede", "Estado", "Inicio", "Acciones"],
            rows_var=state.tournaments,
            row_renderer=lambda tournament: rx.table.row(
                rx.table.cell(tournament["name"], color="black"),
                rx.table.cell(tournament["venue"], color="black"),
                rx.table.cell(tournament["status"], color="black"),
                rx.table.cell(tournament["start_date"], color="black"),
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
                subtitle="Creá un torneo para comenzar a gestionar la competencia",
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
            add_label="Añadir Atleta",
            on_add_click=state.set_form_values,
            import_label="Importar",
            export_label="Exportar",
            on_import_click=state.import_athletes,
            on_export_click=state.export_athletes,
        ),
        registry_error(state.error_message),
        rx.cond(state.show_form, _athlete_form(), _athletes_card()),
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
            add_label="Añadir Árbitro",
            on_add_click=state.set_form_values,
            import_label="Importar",
            export_label="Exportar",
            on_import_click=state.import_referees,
            on_export_click=state.export_referees,
        ),
        registry_error(state.error_message),
        rx.cond(state.show_form, _referee_form(), _referees_card()),
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
