"""Tournament operator workspace page — sequential card flow."""

import reflex as rx

from kakumi_app.components.registry_crud import registry_page_shell
from kakumi_app.pages.registries import _tournament_form
from kakumi_app.states.tournament_category_state import TournamentCategoryState
from kakumi_app.states.tournament_crud_state import TournamentCrudState
from kakumi_app.states.tournament_state import (
    CATEGORIES_STEP,
    CONFIRM_STEP,
    EDIT_CHOICE_STEP,
    FORM_STEP,
    SELECTION_STEP,
    STATUS_STEP,
    TATAMIS_STEP,
    TournamentState,
)
from kakumi_app.states.tournament_tatami_state import TournamentTatamiState
from kakumi_app.styles.tokens import BRAND_RED


def _workspace_header() -> rx.Component:
    """Render workspace page heading."""
    return rx.vstack(
        rx.heading("Torneo", size="8"),
        rx.text("Gestiona el ciclo competitivo, categorías y tatamis."),
        spacing="1",
        align="start",
        width="100%",
    )


def _step_indicator() -> rx.Component:
    """Progress dots. Hidden on step 0. Visited/current dots in brand red."""
    return rx.cond(
        TournamentState.step_index > 0,
        rx.hstack(
            rx.foreach(
                TournamentState._step_labels,
                lambda label, idx: rx.tooltip(
                    rx.box(
                        width="12px",
                        height="12px",
                        border_radius="50%",
                        bg=rx.cond(
                            TournamentState.step_index >= idx,
                            BRAND_RED,
                            "gray.300",
                        ),
                        opacity=rx.cond(
                            TournamentState.step_index == idx,
                            "1",
                            rx.cond(
                                TournamentState.step_index > idx,
                                "0.8",
                                "0.4",
                            ),
                        ),
                        role="img",
                        aria_current=rx.cond(
                            TournamentState.step_index == idx,
                            "step",
                            None,
                        ),
                    ),
                    label=label,
                ),
            ),
            role="navigation",
            aria_label="Progreso del flujo",
            justify="center",
            spacing="3",
            width="100%",
            padding_y="2",
        ),
    )


def _navigation_bar() -> rx.Component:
    """Render Anterior/Siguiente buttons. Context-sensitive labels."""
    state = TournamentState
    return rx.hstack(
        rx.button(
            "← Anterior",
            on_click=state.go_previous,
            disabled=~state.can_go_previous,
            variant="outline",
            width={"base": "100%", "md": "auto"},
        ),
        rx.hstack(
            rx.cond(
                (TournamentState.step_index == CONFIRM_STEP)
                & TournamentState.create_mode,
                rx.button(
                    "Comenzar torneo",
                    on_click=state.complete_create_flow,
                    color_scheme="green",
                    width={"base": "100%", "md": "auto"},
                ),
                rx.button(
                    rx.cond(
                        TournamentState.step_index >= TournamentState._step_count - 1,
                        "Finalizar",
                        "Siguiente →",
                    ),
                    on_click=state.go_next,
                    disabled=~state.can_go_next,
                    color_scheme="red",
                    width={"base": "100%", "md": "auto"},
                ),
            ),
        ),
        justify="between",
        width="100%",
        padding_top="4",
        direction={"base": "column", "md": "row"},
        align="stretch",
    )


def _selector_card() -> rx.Component:
    """Card 0: Tournament selection with create/edit action buttons."""
    state = TournamentState
    return rx.card(
        rx.vstack(
            rx.heading("Torneos disponibles", size="5"),
            rx.cond(
                state.tournaments.length() == 0,
                rx.text("No hay torneos cargados todavía."),
                rx.foreach(
                    state.tournaments,
                    lambda tournament: rx.button(
                        tournament["name"],
                        width="100%",
                        variant=rx.cond(
                            state.current_tournament,
                            rx.cond(
                                state.current_tournament["id"] == tournament["id"],
                                "solid",
                                "outline",
                            ),
                            "outline",
                        ),
                        on_click=state.set_current_tournament(tournament["id"]),
                    ),
                ),
            ),
            rx.cond(
                state.show_lifecycle_controls,
                rx.hstack(
                    rx.button(
                        "Crear torneo",
                        on_click=state.start_create_flow,
                        color_scheme="green",
                    ),
                    rx.button(
                        "Editar torneo",
                        on_click=state.start_edit_flow,
                        variant="outline",
                    ),
                    spacing="2",
                    width="100%",
                    justify="center",
                ),
            ),
            spacing="3",
            align="stretch",
            width="100%",
        ),
        width="100%",
        role="region",
        aria_label="Selección de torneo",
    )


def _selection_summary() -> rx.Component:
    """Render currently selected tournament summary."""
    state = TournamentState
    return rx.cond(
        state.current_tournament,
        rx.vstack(
            rx.heading(state.current_tournament["name"], size="5"),
            rx.text(
                f"Estado actual: {state.current_tournament['status']}",
            ),
            rx.text(f"Sede: {state.current_tournament['venue']}"),
            rx.text(
                f"Tatamis declarados: {state.current_tournament['tatami_count']}",
            ),
            rx.link(
                rx.button(
                    "Ver bracket / Pantalla de competencia",
                    variant="surface",
                    size="2",
                ),
                href=f"/tournaments/{state.current_tournament['id']}/bracket",
                underline="none",
            ),
            spacing="2",
            align="start",
            width="100%",
        ),
        rx.text("Selecciona un torneo para ver sus detalles operativos."),
    )


def _lifecycle_buttons() -> rx.Component:
    """Render lifecycle action buttons (extracted from old _lifecycle_card)."""
    state = TournamentState
    return rx.vstack(
        rx.hstack(
            rx.cond(
                state.show_open_registrations_action,
                rx.button(
                    "Abrir inscripciones",
                    on_click=state.open_registrations,
                    disabled=~state.has_selected_tournament,
                ),
                rx.fragment(),
            ),
            rx.cond(
                state.show_close_registrations_action,
                rx.button(
                    "Cerrar inscripciones",
                    on_click=state.close_registrations,
                    disabled=~state.has_selected_tournament,
                ),
                rx.fragment(),
            ),
            rx.cond(
                state.show_start_competition_action,
                rx.button(
                    "Iniciar competencia",
                    on_click=state.start_competition,
                    disabled=~state.has_selected_tournament,
                ),
                rx.fragment(),
            ),
            wrap="wrap",
            spacing="2",
        ),
        rx.hstack(
            rx.cond(
                state.show_finish_competition_action,
                rx.button(
                    "Finalizar torneo",
                    variant="outline",
                    on_click=state.finish_competition,
                    disabled=~state.has_selected_tournament,
                ),
                rx.fragment(),
            ),
            rx.cond(
                state.show_archive_tournament_action,
                rx.button(
                    "Archivar torneo",
                    variant="outline",
                    on_click=state.archive_tournament,
                    disabled=~state.has_selected_tournament,
                ),
                rx.fragment(),
            ),
            rx.cond(
                state.show_reopen_registrations_action,
                rx.button(
                    "Reabrir inscripciones",
                    variant="outline",
                    on_click=state.reopen_registrations,
                    disabled=~state.has_selected_tournament,
                ),
                rx.fragment(),
            ),
            rx.cond(
                state.show_cancel_tournament_action,
                rx.button(
                    "Cancelar torneo",
                    variant="outline",
                    on_click=state.cancel_tournament,
                    disabled=~state.has_selected_tournament,
                ),
                rx.fragment(),
            ),
            spacing="2",
            wrap="wrap",
        ),
        spacing="2",
        width="100%",
    )


def _categories_card() -> rx.Component:
    """Card 3: Categories CRUD with readonly mode guard."""
    state = TournamentCategoryState
    ts = TournamentState
    return rx.card(
        rx.vstack(
            rx.heading("Categorías manuales", size="5"),
            rx.text("Administra categorías creadas manualmente."),
            rx.cond(
                state.error_message,
                rx.callout(
                    state.error_message,
                    icon="triangle_alert",
                    color_scheme="red",
                ),
                rx.fragment(),
            ),
            rx.cond(
                state.has_selected_tournament_context,
                rx.vstack(
                    rx.hstack(
                        rx.heading(
                            "Categorías del torneo seleccionado",
                            size="4",
                        ),
                        rx.cond(
                            ~ts.is_readonly_mode,
                            rx.button(
                                "Nueva categoría",
                                on_click=state.set_form_values,
                            ),
                        ),
                        justify="between",
                        width="100%",
                        align="center",
                    ),
                    rx.text(state.current_tournament_name),
                    rx.cond(
                        state.show_form,
                        rx.form(
                            rx.vstack(
                                rx.heading(
                                    rx.cond(
                                        state.is_editing,
                                        "Editar categoría",
                                        "Nueva categoría",
                                    ),
                                    size="4",
                                ),
                                rx.input(
                                    placeholder="Nombre categoría",
                                    value=state.name,
                                    on_change=state.set_name,
                                ),
                                rx.select(
                                    state.modality_options,
                                    value=state.modality,
                                    on_change=state.set_modality,
                                ),
                                rx.select(
                                    state.gender_options,
                                    value=state.gender,
                                    on_change=state.set_gender,
                                ),
                                rx.hstack(
                                    rx.input(
                                        placeholder="Edad mínima",
                                        value=state.min_age,
                                        on_change=state.set_min_age,
                                        type="number",
                                    ),
                                    rx.input(
                                        placeholder="Edad máxima",
                                        value=state.max_age,
                                        on_change=state.set_max_age,
                                        type="number",
                                    ),
                                    width="100%",
                                ),
                                rx.hstack(
                                    rx.select(
                                        state.belt_rank_options,
                                        value=state.min_belt_rank,
                                        on_change=state.set_min_belt_rank,
                                        placeholder="Grado mínimo",
                                    ),
                                    rx.select(
                                        state.belt_rank_options,
                                        value=state.max_belt_rank,
                                        on_change=state.set_max_belt_rank,
                                        placeholder="Grado máximo",
                                    ),
                                    width="100%",
                                ),
                                rx.hstack(
                                    rx.select(
                                        state.competition_system_options,
                                        value=state.competition_system,
                                        on_change=state.set_competition_system,
                                    ),
                                    rx.select(
                                        state.bracket_size_options,
                                        value=state.bracket_size,
                                        on_change=state.set_bracket_size,
                                    ),
                                    width="100%",
                                ),
                                rx.cond(
                                    (state.modality == "Kata Individual")
                                    | (state.modality == "Kata por Equipos"),
                                    rx.vstack(
                                        rx.select(
                                            ["3", "5", "7"],
                                            value=state.form_judge_panel_size,
                                            on_change=state.set_judge_panel_size,
                                        ),
                                        rx.select(
                                            ["STANDARD", "INFORMAL"],
                                            value=state.form_kata_flow_mode,
                                            on_change=state.set_kata_flow_mode,
                                        ),
                                        rx.cond(
                                            state.form_kata_flow_mode == "INFORMAL",
                                            rx.text(
                                                "INFORMAL (automático)",
                                                color_scheme="gray",
                                            ),
                                            rx.select(
                                                [
                                                    "average-with-discard",
                                                    "majority-by-judge",
                                                ],
                                                value=state.form_scoring_type,
                                                on_change=state.set_scoring_type,
                                            ),
                                        ),
                                        spacing="3",
                                        width="100%",
                                    ),
                                ),
                                rx.hstack(
                                    rx.button(
                                        "Guardar categoría",
                                        type="submit",
                                    ),
                                    rx.button(
                                        "Cancelar",
                                        variant="outline",
                                        on_click=state.cancel_category_form,
                                    ),
                                    spacing="2",
                                ),
                                width="100%",
                                spacing="3",
                                align="stretch",
                            ),
                            on_submit=state.save_category,
                            width="100%",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        state.categories,
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("Nombre"),
                                    rx.table.column_header_cell("Clasificación"),
                                    rx.table.column_header_cell("Sistema"),
                                    rx.table.column_header_cell("Acciones"),
                                )
                            ),
                            rx.table.body(
                                rx.foreach(
                                    state.categories,
                                    lambda category: rx.table.row(
                                        rx.table.cell(category["name"]),
                                        rx.table.cell(
                                            rx.fragment(
                                                f"{category['gender']} · {category['min_age']}-{category['max_age']}"  # noqa
                                            ),
                                        ),
                                        rx.table.cell(
                                            category["competition_system"],
                                        ),
                                        rx.table.cell(
                                            rx.cond(
                                                ~ts.is_readonly_mode,
                                                rx.hstack(
                                                    rx.button(
                                                        "Editar",
                                                        size="2",
                                                        on_click=lambda event: (
                                                            state.set_form_values(
                                                                event,
                                                                category,
                                                            )
                                                        ),
                                                    ),
                                                    rx.button(
                                                        "Eliminar categoría",
                                                        size="2",
                                                        variant="outline",
                                                        on_click=lambda: (
                                                            state.delete_category(
                                                                category["id"]
                                                            )
                                                        ),
                                                    ),
                                                    spacing="2",
                                                ),
                                            ),
                                        ),
                                    ),
                                )
                            ),
                            width="100%",
                        ),
                        rx.text(
                            "No hay categorías manuales cargadas todavía.",
                        ),
                    ),
                    width="100%",
                    spacing="3",
                    align="stretch",
                ),
                rx.text(
                    "Selecciona un torneo para administrar sus categorías.",
                ),
            ),
            spacing="3",
            align="start",
            width="100%",
        ),
        width="100%",
        role="region",
        aria_label="Categorías del torneo",
    )


def _tatami_card() -> rx.Component:
    """Card 4: Tatami CRUD with readonly mode guard."""
    state = TournamentTatamiState
    ts = TournamentState
    return rx.card(
        rx.vstack(
            rx.heading(
                "Tatamis",
                size="5",
            ),
            rx.text(
                "Áreas oficiales para el desarrollo del torneo",
            ),
            rx.cond(
                state.error_message,
                rx.callout(
                    state.error_message,
                    icon="triangle_alert",
                    color_scheme="red",
                ),
                rx.fragment(),
            ),
            rx.cond(
                state.has_selected_tournament_context,
                rx.vstack(
                    rx.hstack(
                        rx.heading(
                            "Tatamis del torneo seleccionado",
                            size="4",
                        ),
                        rx.cond(
                            ~ts.is_readonly_mode,
                            rx.button(
                                "Nuevo tatami",
                                on_click=state.set_form_values,
                            ),
                        ),
                        justify="between",
                        width="100%",
                        align="center",
                    ),
                    rx.text(
                        state.current_tournament_name,
                    ),
                    rx.hstack(
                        rx.badge(
                            f"Tatamis declarados: {state.declared_tatami_count}",
                            color_scheme="blue",
                        ),
                        rx.badge(
                            f"Tatamis activos: {state.active_tatami_count}",
                            color_scheme="green",
                        ),
                        wrap="wrap",
                        spacing="2",
                    ),
                    rx.cond(
                        state.show_form,
                        rx.form(
                            rx.vstack(
                                rx.heading(
                                    rx.cond(
                                        state.is_editing,
                                        "Editar tatami",
                                        "Nuevo tatami",
                                    ),
                                    size="4",
                                ),
                                rx.input(
                                    placeholder="Nombre tatami",
                                    value=state.name,
                                    on_change=state.set_name,
                                ),
                                rx.input(
                                    placeholder="Ubicación / referencia",
                                    value=state.location,
                                    on_change=state.set_location,
                                ),
                                rx.hstack(
                                    rx.button("Guardar tatami", type="submit"),
                                    rx.button(
                                        "Cancelar",
                                        variant="outline",
                                        on_click=state.cancel_tatami_form,
                                    ),
                                    spacing="2",
                                ),
                                width="100%",
                                spacing="3",
                                align="stretch",
                            ),
                            on_submit=state.save_tatami,
                            width="100%",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        state.tatamis,
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("Tatami"),
                                    rx.table.column_header_cell("Ubicación"),
                                    rx.table.column_header_cell("Estado"),
                                    rx.table.column_header_cell("Acciones"),
                                )
                            ),
                            rx.table.body(
                                rx.foreach(
                                    state.tatamis,
                                    lambda tatami: rx.table.row(
                                        rx.table.cell(tatami["name"]),
                                        rx.table.cell(
                                            rx.cond(
                                                tatami["location"],
                                                tatami["location"],
                                                "Sin referencia",
                                            ),
                                        ),
                                        rx.table.cell(
                                            rx.badge(
                                                rx.cond(
                                                    tatami["is_active"],
                                                    "Activo",
                                                    "Inactivo",
                                                ),
                                                color_scheme=rx.cond(
                                                    tatami["is_active"],
                                                    "green",
                                                    "gray",
                                                ),
                                            ),
                                        ),
                                        rx.table.cell(
                                            rx.cond(
                                                ~ts.is_readonly_mode,
                                                rx.hstack(
                                                    rx.button(
                                                        "Editar",
                                                        size="2",
                                                        on_click=lambda event: (
                                                            state.set_form_values(
                                                                event,
                                                                tatami,
                                                            )
                                                        ),
                                                    ),
                                                    rx.button(
                                                        rx.cond(
                                                            tatami["is_active"],
                                                            "Desactivar",
                                                            "Activar",
                                                        ),
                                                        size="2",
                                                        variant="outline",
                                                        on_click=lambda: (
                                                            state.toggle_tatami_active(
                                                                tatami["id"]
                                                            )
                                                        ),
                                                    ),
                                                    rx.button(
                                                        "Eliminar tatami",
                                                        size="2",
                                                        variant="outline",
                                                        on_click=lambda: (
                                                            state.delete_tatami(
                                                                tatami["id"]
                                                            )
                                                        ),
                                                    ),
                                                    spacing="2",
                                                    wrap="wrap",
                                                ),
                                            ),
                                        ),
                                    ),
                                )
                            ),
                            width="100%",
                        ),
                        rx.text("No hay tatamis configurados todavía."),
                    ),
                    width="100%",
                    spacing="3",
                    align="stretch",
                ),
                rx.text("Selecciona un torneo para administrar tatamis."),
            ),
            spacing="3",
            align="start",
            width="100%",
        ),
        width="100%",
        role="region",
        aria_label="Tatamis del torneo",
    )


def _qr_section() -> rx.Component:
    """Render QR content inline (no card wrapper).

    Includes download link, copy-link button, and large QR dialog.
    """
    state = TournamentState
    return rx.vstack(
        rx.heading("QR de Espectadores", size="5"),
        rx.text(
            "Genera un código QR para que los espectadores accedan "
            "al dashboard del torneo.",
        ),
        rx.cond(
            state.qr_data_url != "",
            rx.vstack(
                # QR image wrapped in download link (Task 2.1)
                rx.link(
                    rx.image(
                        src=state.qr_data_url,
                        width="200px",
                        height="200px",
                    ),
                    href=state.qr_data_url,
                    download="kakumi-qr.png",
                ),
                rx.text(f"Código: {state.qr_code_text}"),
                rx.text(f"Expira: {state.qr_expires_at}", font_size="sm"),
                # Actions row: regenerate, copy link, large view (Tasks 2.2, 2.3)
                rx.hstack(
                    rx.button(
                        "Regenerar QR",
                        on_click=state.regenerate_qr,
                        variant="outline",
                    ),
                    rx.button(
                        "Copiar enlace",
                        on_click=rx.set_clipboard(state.qr_viewer_url),
                        variant="outline",
                    ),
                    rx.dialog.root(
                        rx.dialog.trigger(
                            rx.button(
                                "Ver QR grande",
                                variant="outline",
                            ),
                        ),
                        rx.dialog.content(
                            rx.dialog.title(
                                "QR de Espectadores",
                                font_weight="bold",
                            ),
                            rx.vstack(
                                rx.image(
                                    src=state.qr_data_url,
                                    width="400px",
                                    height="400px",
                                ),
                                rx.text(
                                    f"Código: {state.qr_code_text}",
                                    font_weight="bold",
                                ),
                                rx.text(
                                    f"Expira: {state.qr_expires_at}",
                                    font_size="sm",
                                ),
                                rx.dialog.close(
                                    rx.button(
                                        "Cerrar",
                                        variant="soft",
                                        color_scheme="gray",
                                    ),
                                ),
                                spacing="3",
                                align="center",
                                width="100%",
                            ),
                        ),
                    ),
                    spacing="3",
                    wrap="wrap",
                ),
                spacing="3",
                align="center",
                width="100%",
            ),
            rx.vstack(
                rx.button(
                    "Generar QR",
                    on_click=state.generate_qr,
                    disabled=~state.has_selected_tournament,
                ),
                spacing="3",
                align="center",
                width="100%",
            ),
        ),
        spacing="3",
        align="start",
        width="100%",
    )


def _status_card() -> rx.Component:
    """Card 1: Tournament summary, lifecycle controls, and QR."""
    state = TournamentState
    return rx.card(
        rx.vstack(
            rx.heading("Estado del torneo", size="5"),
            _selection_summary(),
            rx.cond(
                state.show_lifecycle_controls,
                rx.vstack(
                    rx.divider(),
                    rx.heading("Controles de ciclo", size="4"),
                    _lifecycle_buttons(),
                    spacing="2",
                    width="100%",
                ),
                rx.cond(
                    state.has_selected_tournament,
                    rx.text("No tienes permisos para operar ciclo de torneo."),
                ),
            ),
            rx.cond(
                state.transition_error,
                rx.callout(state.transition_error, icon="triangle_alert", color="red"),
            ),
            rx.divider(),
            _qr_section(),
            spacing="3",
            align="start",
            width="100%",
        ),
        width="100%",
        role="region",
        aria_label="Estado del torneo",
    )


def _form_card() -> rx.Component:
    """Card 2: Tournament create/edit form (bridged via TournamentState)."""
    state = TournamentState
    return rx.card(
        rx.vstack(
            rx.heading(
                rx.cond(state.create_mode, "Crear torneo", "Editar torneo"),
                size="5",
            ),
            _tournament_form(
                on_submit_override=TournamentState.handle_form_submit,
                on_cancel_override=TournamentState.cancel_create_flow,
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
        role="region",
        aria_label=rx.cond(state.create_mode, "Formulario de creación", "Formulario de edición"),
    )


def _registration_control_card() -> rx.Component:
    """Card 5: Create flow — review and start competition."""
    state = TournamentState
    return rx.card(
        rx.vstack(
            rx.heading("Confirmar inicio", size="5"),
            rx.text("El torneo se creó correctamente."),
            rx.text("Revisa categorías y tatamis antes de iniciar."),
            rx.text(
                "Al clickear 'Comenzar torneo' se iniciará la competencia.",
                font_size="sm",
            ),
            rx.divider(),
            rx.cond(
                state.current_tournament,
                rx.text(f"Torneo: {state.current_tournament['name']}", weight="bold"),
            ),
            spacing="3",
            align="start",
            width="100%",
        ),
        width="100%",
        role="region",
        aria_label="Confirmar inicio de torneo",
    )


def _edit_choice_card() -> rx.Component:
    """Card 6: Edit flow — choose what to edit."""
    state = TournamentState
    return rx.card(
        rx.vstack(
            rx.heading("¿Qué deseas editar?", size="5"),
            rx.cond(
                state.current_tournament,
                rx.text(f"Torneo: {state.current_tournament['name']}"),
                rx.text("Selecciona un torneo"),
            ),
            rx.vstack(
                rx.button(
                    "Editar categorías",
                    on_click=state.go_to_step(CATEGORIES_STEP),
                    width="100%",
                ),
                rx.cond(
                    ~state.is_readonly_mode,
                    rx.button(
                        "Editar datos del torneo",
                        on_click=state.go_to_step(FORM_STEP),
                        width="100%",
                        variant="outline",
                    ),
                ),
                spacing="2",
                width="100%",
            ),
            rx.cond(
                state.is_readonly_mode,
                rx.callout(
                    "Solo visualización disponible para torneos avanzados.",
                    icon="info",
                ),
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
        role="region",
        aria_label="Opciones de edición",
    )


def _active_card() -> rx.Component:
    """Dispatch to the correct card component based on step_index."""
    return rx.box(
        rx.match(
            TournamentState.step_index,
            (SELECTION_STEP, _selector_card()),
            (STATUS_STEP, _status_card()),
            (FORM_STEP, _form_card()),
            (CATEGORIES_STEP, _categories_card()),
            (TATAMIS_STEP, _tatami_card()),
            (CONFIRM_STEP, _registration_control_card()),
            (EDIT_CHOICE_STEP, _edit_choice_card()),
            _selector_card(),
        ),
        style={
            "transition": "opacity 0.2s ease, transform 0.2s ease",
        },
        key=TournamentState.step_index,
        role="region",
        aria_live="polite",
        aria_label=f"Paso actual del torneo",
        width="100%",
    )


def tournament() -> rx.Component:
    """Render tournament operator workspace shell — sequential card flow."""
    body = rx.vstack(
        _workspace_header(),
        _step_indicator(),
        _active_card(),
        _navigation_bar(),
        spacing="4",
        width="100%",
        max_width="800px",
        margin_x="auto",
    )
    return registry_page_shell(body=body)
