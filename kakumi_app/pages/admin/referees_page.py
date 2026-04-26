"""
Referees Admin Page
CRUD operations for referees.
"""

import reflex as rx

from kakumi_app.components.sidebar import sidebar
from kakumi_app.states.referee_state import RefereeState


def referees_table() -> rx.Component:
    """Table displaying referees."""
    state = RefereeState

    return rx.vstack(
        rx.hstack(
            rx.input(
                placeholder="Buscar árbitros...",
                on_change=state.set_search_query,
                width="300px",
            ),
            rx.button(
                "Buscar",
                on_click=state.filter_referees,
                color_scheme="blue",
            ),
            rx.button(
                "+ Nuevo Árbitro",
                on_click=state.set_form_values,
                color_scheme="green",
            ),
            spacing="4",
            margin_bottom="1em",
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
                    rx.table.column_header_cell("Licencia"),
                    rx.table.column_header_cell("Nivel"),
                    rx.table.column_header_cell("Rol"),
                    rx.table.column_header_cell("Disponible"),
                    rx.table.column_header_cell("Dojo"),
                    rx.table.column_header_cell("Acciones"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    state.referees,
                    lambda referee: rx.table.row(
                        rx.table.cell(referee["id"]),
                        rx.table.cell(referee["name"]),
                        rx.table.cell(referee["license_number"]),
                        rx.table.cell(referee["license_level"]),
                        rx.table.cell(referee["role"]),
                        rx.table.cell(rx.cond(referee["is_available"], "Sí", "No")),
                        rx.table.cell(rx.cond(referee["dojo"], referee["dojo"], "-")),
                        rx.table.cell(
                            rx.hstack(
                                rx.button(
                                    "Editar",
                                    on_click=lambda event: state.set_form_values(
                                        event, referee
                                    ),
                                    color_scheme="blue",
                                    size="2",
                                ),
                                rx.button(
                                    "Eliminar",
                                    on_click=lambda: state.delete_referee(
                                        referee["id"]
                                    ),
                                    color_scheme="red",
                                    size="2",
                                ),
                                spacing="2",
                            )
                        ),
                    ),
                ),
            ),
            width="100%",
        ),
        width="100%",
    )


def referee_form() -> rx.Component:
    """Form for creating/editing referee."""
    state = RefereeState

    return rx.box(
        rx.vstack(
            rx.heading(
                rx.cond(
                    state.is_editing,
                    "Editar Árbitro",
                    "Crear Árbitro",
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
                        placeholder="Número de Licencia *",
                        value=state.license_number,
                        on_change=state.set_license_number,
                        width="100%",
                        required=True,
                    ),
                    rx.select(
                        ["NATIONAL", "INTERNATIONAL"],
                        value=state.license_level,
                        on_change=state.set_license_level,
                        width="100%",
                    ),
                    rx.select(
                        ["REFEREE", "JUDGE", "TABLE_OFFICIAL", "SUPERVISOR"],
                        value=state.role,
                        on_change=state.set_role,
                        width="100%",
                    ),
                    rx.input(
                        placeholder="Certificaciones Tatami (JSON)",
                        value=state.tatami_certified,
                        on_change=state.set_tatami_certified,
                        width="100%",
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
                        width="100%",
                    ),
                    rx.input(
                        placeholder="Email",
                        value=state.email,
                        on_change=state.set_email,
                        width="100%",
                        type="email",
                    ),
                    rx.input(
                        placeholder="Teléfono",
                        value=state.phone,
                        on_change=state.set_phone,
                        width="100%",
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
                        spacing="4",
                        margin_top="1em",
                    ),
                    spacing="4",
                ),
                on_submit=state.save_referee,
            ),
        ),
        padding="2em",
        border="1px solid #ddd",
        border_radius="8px",
        margin_bottom="2em",
    )


def referees_page() -> rx.Component:
    """Main referees admin page."""
    state = RefereeState

    return rx.box(
        rx.vstack(
            rx.hstack(
                sidebar(),
                rx.vstack(
                    rx.heading(
                        "Gestión de Árbitros",
                        font_size="3xl",
                        font_weight="bold",
                        color="black",
                        margin_bottom="0.5em",
                    ),
                    rx.text(
                        "Administrar árbitros registrados",
                        font_size="md",
                        color="gray",
                        margin_bottom="1em",
                    ),
                    rx.cond(
                        state.show_form,
                        referee_form(),
                        referees_table(),
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


@rx.page(route="/admin/referees")
def referees() -> rx.Component:
    """Route for referees page."""
    return referees_page()


@rx.page(
    route="/admin/referees/new",
    on_load=lambda: RefereeState.set_form_values(None),
)
def new_referee() -> rx.Component:
    """Route for new referee form."""
    return referees_page()
