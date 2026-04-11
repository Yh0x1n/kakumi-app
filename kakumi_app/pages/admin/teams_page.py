"""
Teams Admin Page
CRUD operations for teams.
"""

import reflex as rx
from kakumi_app.states.team_state import TeamState
from kakumi_app.components.sidebar import sidebar


def teams_table() -> rx.Component:
    """Table displaying teams."""
    state = TeamState

    return rx.vstack(
        rx.hstack(
            rx.input(
                placeholder="Buscar equipos...",
                on_change=state.set_search_query,
                width="300px",
            ),
            rx.button(
                "Buscar",
                on_click=state.filter_teams,
                color_scheme="blue",
            ),
            rx.button(
                "+ Nuevo Equipo",
                on_click=state.set_form_values,
                color_scheme="green",
            ),
            spacing="1em",
            margin_bottom="1em",
        ),
        rx.cond(
            state.success_message,
            rx.callout(
                state.success_message,
                icon="check-circle",
                color_scheme="green",
                margin_bottom="1em",
            ),
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
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("ID"),
                    rx.table.column_header_cell("Nombre"),
                    rx.table.column_header_cell("Dojo"),
                    rx.table.column_header_cell("Categoría"),
                    rx.table.column_header_cell("Miembros"),
                    rx.table.column_header_cell("Activo"),
                    rx.table.column_header_cell("Acciones"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    state.teams,
                    lambda team: rx.table.row(
                        rx.table.cell(team.id),
                        rx.table.cell(team.name),
                        rx.table.cell(team.dojo or "-"),
                        rx.table.cell(team.category_id),  # Could show category name
                        rx.table.cell(team.member_count),
                        rx.table.cell("Sí" if team.is_active else "No"),
                        rx.table.cell(
                            rx.hstack(
                                rx.button(
                                    "Editar",
                                    on_click=lambda event: state.set_form_values(
                                        event, team
                                    ),
                                    color_scheme="blue",
                                    size="sm",
                                ),
                                rx.button(
                                    "Eliminar",
                                    on_click=lambda: state.delete_team(team.id),
                                    color_scheme="red",
                                    size="sm",
                                ),
                                spacing="0.5em",
                            )
                        ),
                    ),
                ),
            ),
            width="100%",
        ),
        width="100%",
    )


def team_form() -> rx.Component:
    """Form for creating/editing team."""
    state = TeamState

    return rx.box(
        rx.vstack(
            rx.heading(
                rx.cond(
                    state.is_editing,
                    "Editar Equipo",
                    "Crear Equipo",
                ),
                font_size="2xl",
                margin_bottom="1em",
            ),
            rx.form(
                rx.vstack(
                    rx.input(
                        placeholder="Nombre *",
                        value=state.name,
                        on_change=state.set_name,
                        width="100%",
                        required=True,
                    ),
                    rx.input(
                        placeholder="Dojo",
                        value=state.dojo,
                        on_change=state.set_dojo,
                        width="100%",
                    ),
                    rx.select(
                        [f"{cat.id}: {cat.name}" for cat in state.categories],
                        value=state.category_id,
                        on_change=state.set_category_id,
                        width="100%",
                        placeholder="Seleccionar categoría *",
                    ),
                    rx.checkbox(
                        "Activo",
                        checked=state.is_active,
                        on_change=state.set_is_active,
                    ),
                    rx.hstack(
                        rx.button(
                            "Guardar",
                            type="submit",
                            color_scheme="green",
                        ),
                        rx.button(
                            "Cancelar",
                            on_click=state.cancel_form,
                            color_scheme="gray",
                        ),
                        spacing="1em",
                        margin_top="1em",
                    ),
                    spacing="1em",
                ),
                on_submit=state.save_team,
            ),
        ),
        padding="2em",
        border="1px solid #ddd",
        border_radius="8px",
        margin_bottom="2em",
    )


def teams_page() -> rx.Component:
    """Main teams admin page."""
    state = TeamState

    return rx.box(
        rx.vstack(
            rx.hstack(
                sidebar(),
                rx.vstack(
                    rx.heading(
                        "Gestión de Equipos",
                        font_size="3xl",
                        font_weight="bold",
                        color="black",
                        margin_bottom="0.5em",
                    ),
                    rx.text(
                        "Administrar equipos registrados",
                        font_size="md",
                        color="gray",
                        margin_bottom="1em",
                    ),
                    rx.cond(
                        state.show_form,
                        team_form(),
                        teams_table(),
                    ),
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


@rx.page(route="/admin/teams")
def teams() -> rx.Component:
    """Route for teams page."""
    return teams_page()


@rx.page(route="/admin/teams/new")
def new_team() -> rx.Component:
    """Route for new team form."""
    state = TeamState
    state.set_form_values(None)
    return teams_page()
