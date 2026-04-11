"""
Athletes Admin Page
CRUD operations for athletes with import functionality.
"""

import reflex as rx
from kakumi_app.states.athlete_state import AthleteState
from kakumi_app.components.sidebar import sidebar


def athletes_table() -> rx.Component:
    """Table displaying athletes."""
    state = AthleteState

    return rx.vstack(
        rx.hstack(
            rx.input(
                placeholder="Buscar atletas...",
                on_change=state.set_search_query,
                width="300px",
            ),
            rx.button(
                "Buscar",
                on_click=state.filter_athletes,
                color_scheme="blue",
            ),
            rx.button(
                "+ Nuevo Atleta",
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
                    rx.table.column_header_cell("Email"),
                    rx.table.column_header_cell("Fecha Nac."),
                    rx.table.column_header_cell("Género"),
                    rx.table.column_header_cell("Peso"),
                    rx.table.column_header_cell("Dojo"),
                    rx.table.column_header_cell("Activo"),
                    rx.table.column_header_cell("Acciones"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    state.athletes,
                    lambda athlete: rx.table.row(
                        rx.table.cell(athlete.id),
                        rx.table.cell(athlete.name),
                        rx.table.cell(athlete.email or "-"),
                        rx.table.cell(athlete.date_of_birth),
                        rx.table.cell(athlete.gender),
                        rx.table.cell(
                            f"{athlete.weight_kg} kg" if athlete.weight_kg else "-"
                        ),
                        rx.table.cell(athlete.dojo or "-"),
                        rx.table.cell("Sí" if athlete.is_active else "No"),
                        rx.table.cell(
                            rx.hstack(
                                rx.button(
                                    "Editar",
                                    on_click=lambda event: state.set_form_values(
                                        event, athlete
                                    ),
                                    color_scheme="blue",
                                    size="sm",
                                ),
                                rx.button(
                                    "Eliminar",
                                    on_click=lambda: state.delete_athlete(athlete.id),
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


def athlete_form() -> rx.Component:
    """Form for creating/editing athlete."""
    state = AthleteState

    return rx.box(
        rx.vstack(
            rx.heading(
                rx.cond(
                    state.is_editing,
                    "Editar Atleta",
                    "Crear Atleta",
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
                        placeholder="Email",
                        value=state.email,
                        on_change=state.set_email,
                        width="100%",
                        type="email",
                    ),
                    rx.input(
                        placeholder="Fecha de Nacimiento (YYYY-MM-DD) *",
                        value=state.date_of_birth,
                        on_change=state.set_date_of_birth,
                        width="100%",
                        required=True,
                    ),
                    rx.select(
                        ["MALE", "FEMALE"],
                        value=state.gender,
                        on_change=state.set_gender,
                        width="100%",
                    ),
                    rx.input(
                        placeholder="Peso (kg)",
                        value=state.weight_kg,
                        on_change=state.set_weight_kg,
                        width="100%",
                        type="number",
                        step="0.1",
                    ),
                    rx.input(
                        placeholder="Grado (ej: Kyu 2, Dan 1)",
                        value=state.belt_rank,
                        on_change=state.set_belt_rank,
                        width="100%",
                    ),
                    rx.input(
                        placeholder="Dojo",
                        value=state.dojo,
                        on_change=state.set_dojo,
                        width="100%",
                    ),
                    rx.input(
                        placeholder="Nacionalidad (ISO 3 letras)",
                        value=state.nationality,
                        on_change=state.set_nationality,
                        width="100%",
                        max_length=3,
                    ),
                    rx.input(
                        placeholder="Número de Licencia",
                        value=state.license_number,
                        on_change=state.set_license_number,
                        width="100%",
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
                on_submit=state.save_athlete,
            ),
        ),
        padding="2em",
        border="1px solid #ddd",
        border_radius="8px",
        margin_bottom="2em",
    )


def athletes_page() -> rx.Component:
    """Main athletes admin page."""
    state = AthleteState

    return rx.box(
        rx.vstack(
            rx.hstack(
                sidebar(),
                rx.vstack(
                    rx.heading(
                        "Gestión de Atletas",
                        font_size="3xl",
                        font_weight="bold",
                        color="black",
                        margin_bottom="0.5em",
                    ),
                    rx.text(
                        "Administrar atletas registrados",
                        font_size="md",
                        color="gray",
                        margin_bottom="1em",
                    ),
                    rx.cond(
                        state.show_form,
                        athlete_form(),
                        athletes_table(),
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


@rx.page(route="/admin/athletes")
def athletes() -> rx.Component:
    """Route for athletes page."""
    return athletes_page()


@rx.page(route="/admin/athletes/new")
def new_athlete() -> rx.Component:
    """Route for new athlete form."""
    state = AthleteState
    state.set_form_values(None)  # Reset form for new athlete
    return athletes_page()
