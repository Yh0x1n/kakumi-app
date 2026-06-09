"""
+------------------------------------------------------+
+             Kakumi Tournament Manager                +
+       Web application for Karate-Do tournaments      +
+------------------------------------------------------+
+           Developed by Yhoxin Rossell                +
+           GitHub: @Yh0x1n                            +
+------------------------------------------------------+
"""

# Imports
import importlib

import reflex as rx

from .components.sidebar import sidebar
from .models.athlete_model import Athlete  # noqa [F401]
from .models.display_model import DisplaySession  # noqa [F401]
from .models.referee_model import Referee  # noqa [F401]
from .models.tournament_model import (  # noqa [F401]
    Tournament,
    TournamentCategory,
)
from .pages.competition import (
    bracket_page,
    category_page,
    kata_live_match_page,
    live_match_page,
)
from .pages.exhibition import exhibition
from .pages.public_display import public_display_page
from .pages.registries import registries
from .pages.results import results
from .pages.tournament import tournament
from .pages.viewer import viewer_dashboard_page, viewer_login_page
from .states.auth_state import DEV_AUTH_BYPASS, AuthState
from .states.bracket_state import BracketState
from .states.competition_category_state import CompetitionCategoryState
from .states.kata_match_state import KataMatchState
from .states.kumite_match_state import KumiteMatchState
from .states.results_state import ResultsState
from .states.secondary_display_state import SecondaryDisplayState
from .states.tournament_state import TournamentState
from .states.viewer_state import ViewerState


class State(rx.State):
    pass


def _register_side_effect_pages() -> None:
    """Import side-effect page modules that self-register via @rx.page."""
    importlib.import_module("kakumi_app.pages.admin.athletes_page")
    importlib.import_module("kakumi_app.pages.admin.export_page")
    importlib.import_module("kakumi_app.pages.admin.import_page")
    importlib.import_module("kakumi_app.pages.admin.referees_page")
    importlib.import_module("kakumi_app.pages.admin.teams_page")
    importlib.import_module("kakumi_app.pages.admin.users_page")
    importlib.import_module("kakumi_app.pages.auth.login")
    importlib.import_module("kakumi_app.pages.auth.change_password")


def index() -> rx.Component:
    content = rx.box(
        rx.vstack(
            rx.hstack(
                sidebar(),
                rx.heading(
                    "Welcome to Kakumi Tournament Manager!",
                    font_size=50,
                    align="left",
                    padding_y="0.5em",
                    font_weight="bold",
                ),
                spacing="4",
            ),
        ),
        rx.center(
            rx.grid(
                rx.foreach(
                    rx.Var.range(4),
                    lambda i: rx.card(
                        rx.link(
                            rx.text(
                                f"Resultado {i + 1}",
                                weight="bold",
                                font_size="10",
                            ),
                            underline="none",
                            height="100%",
                        ),
                        border_width="thick",
                        border_radius="1em",
                    ),
                ),
                columns="2",
                spacing="4",
                width="50%",
                padding="0.5em",
            ),
        ),
        height="100vh",
    )

    # Auth guard handled by on_load=AuthState.check_auth_redirect in app.add_page.
    # DEV_AUTH_BYPASS skips the guard entirely (plain Python bool).
    if DEV_AUTH_BYPASS:
        return content
    return content


app = rx.App(theme=rx.theme(appearance="dark", has_background=True))
_register_side_effect_pages()
app.add_page(
    index, title="Kakumi Tournament Manager", on_load=AuthState.check_auth_redirect
)
app.add_page(registries, title="Kakumi | Registros")
app.add_page(
    tournament, title="Kakumi | Torneo", on_load=TournamentState.load_workspace
)
app.add_page(exhibition, title="Kakumi | Exhibición")
app.add_page(
    results, title="Kakumi | Resultados", on_load=ResultsState.load_results_index
)
app.add_page(
    bracket_page,
    route="/tournaments/[id]/bracket",
    title="Kakumi | Bracket",
    on_load=BracketState.load_bracket,
)
app.add_page(
    category_page,
    route="/competition/category/[id]",
    title="Kakumi | Competencia",
    on_load=CompetitionCategoryState.load_category,
)
app.add_page(
    live_match_page,
    route="/competition/match/[id]/kumite",
    title="Kakumi | Kumite en vivo",
    on_load=KumiteMatchState.load_match,
)
app.add_page(
    kata_live_match_page,
    route="/competition/match/[id]/kata",
    title="Kakumi | Kata en vivo",
    on_load=KataMatchState.load_match,
)
app.add_page(
    public_display_page,
    route="/display/[display_key]",
    title="Kakumi | Pantalla pública",
    on_load=[
        SecondaryDisplayState.load_display,
        SecondaryDisplayState.poll_snapshot_loop,
    ],
)
app.add_page(
    viewer_login_page,
    route="/viewer",
    title="Kakumi | Acceso espectadores",
)
app.add_page(
    viewer_dashboard_page,
    route="/viewer/dashboard/[tournament_id]",
    title="Kakumi | Dashboard espectador",
    on_load=ViewerState.load_viewer_dashboard,
)
