"""Legacy referees admin aliases backed by shared registries flow."""

import reflex as rx

from kakumi_app.states.referee_state import RefereeState


@rx.page(route="/admin/referees", on_load=rx.redirect("/registries/referees"))
def referees() -> rx.Component:
    """Legacy alias route for registries referees CRUD."""
    return rx.box(
        rx.text("Redirigiendo a Registro de Árbitros..."),
        width="100%",
        min_height="40vh",
    )


@rx.page(
    route="/admin/referees/new",
    on_load=[RefereeState.set_form_values(None), rx.redirect("/registries/referees")],
)
def new_referee() -> rx.Component:
    """Legacy alias route to open shared referees create flow."""
    return referees()
