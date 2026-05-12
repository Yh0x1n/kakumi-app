"""Legacy athletes admin aliases backed by shared registries flow."""

import reflex as rx

from kakumi_app.states.athlete_state import AthleteState


@rx.page(route="/admin/athletes", on_load=rx.redirect("/registries/athletes"))
def athletes() -> rx.Component:
    """Legacy alias route for registries athletes CRUD."""
    return rx.box(
        rx.text("Redirigiendo a Registro de Atletas..."),
        width="100%",
        min_height="40vh",
    )


@rx.page(
    route="/admin/athletes/new",
    on_load=[AthleteState.set_form_values(None), rx.redirect("/registries/athletes")],
)
def new_athlete() -> rx.Component:
    """Legacy alias route to open shared athletes create flow."""
    return athletes()
