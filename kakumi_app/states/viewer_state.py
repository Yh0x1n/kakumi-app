"""
Viewer State
Manages viewer code validation and access to tournament data.
"""

import logging
from typing import Any, Optional

import reflex as rx
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.referee_model import Referee
from kakumi_app.models.team_model import Team
from kakumi_app.models.tournament_model import (
    Match,
    Tatami,
    Tournament,
    TournamentCategory,
)
from kakumi_app.services.viewer_service import ViewerService
from kakumi_app.utils import (
    BracketCategoryData,
    BracketRoundData,
    build_match_cards,
    group_matches_by_round,
)

logger = logging.getLogger(__name__)


class ViewerState(rx.State):
    """State for viewer access management."""

    # Viewer code stored locally
    viewer_code: str = rx.LocalStorage()

    # Current tournament (if code valid)
    current_tournament: Optional[dict[str, Any]] = None

    # Categories for the tournament (list of dicts)
    categories: list[dict[str, Any]] = []

    # Selected category for bracket/live view
    selected_category_id: Optional[int] = None
    selected_category_type: Optional[str] = None  # "kata" or "kumite"

    # UI state
    is_loading: bool = False
    access_denied: bool = False

    @rx.event
    def set_viewer_code(self, code: str) -> None:
        """Set the viewer code from input."""
        self.viewer_code = code

    @rx.event
    async def validate_and_load_tournament(self) -> Any:
        """Validate the viewer code and load the associated tournament."""
        self.is_loading = True

        if not self.viewer_code:
            self.is_loading = False
            return rx.toast.error("Por favor ingrese un código de espectador.")

        tournament = ViewerService.validate_viewer_code(self.viewer_code)
        if tournament:
            tournament_payload = tournament.model_dump(mode="json")
            tournament_payload["date"] = tournament_payload.get("start_date", "")
            self.current_tournament = tournament_payload
            self.access_denied = False
            await self.load_categories()
            self.is_loading = False
            return rx.toast.success("Acceso de espectador validado")
        else:
            self.current_tournament = None
            self.access_denied = True
            self.is_loading = False
            return rx.toast.error("Código de espectador inválido.")

        self.is_loading = False

    @rx.event
    def clear_viewer_session(self) -> None:
        """Clear viewer session (logout)."""
        self.viewer_code = ""
        self.current_tournament = None
        self.categories = []
        self.selected_category_id = None
        self.selected_category_type = None
        self.access_denied = False

    @rx.event
    async def load_categories(self) -> None:
        """Load categories from current tournament."""
        self.categories = []
        if not self.current_tournament:
            return
        tournament_id = self.current_tournament.get("id")
        if not tournament_id:
            return

        with rx.session() as session:
            categories = session.exec(
                select(TournamentCategory).where(
                    TournamentCategory.tournament_id == int(tournament_id)
                )
            ).all()

        self.categories = [
            {
                "id": category.id,
                "name": category.name,
                "type": (
                    "kata" if str(category.modality).startswith("KATA") else "kumite"
                ),
            }
            for category in categories
        ]

    # Bracket data for live viewer
    bracket_data: Optional[dict[str, Any]] = None
    is_loading_bracket: bool = False

    @rx.event
    def select_category(self, category_id: int, category_type: str) -> None:
        """Select a category for viewing bracket and live match."""
        self.selected_category_id = category_id
        self.selected_category_type = category_type

    @rx.event
    async def load_category_bracket(self) -> None:
        """Load bracket data for the selected category."""
        if self.selected_category_id is None:
            return

        self.is_loading_bracket = True
        self.bracket_data = None

        try:
            category_id = self.selected_category_id

            with rx.session() as session:
                category = session.get(TournamentCategory, category_id)
                if category is None:
                    return

                matches = session.exec(
                    select(Match)
                    .where(Match.category_id == category_id)
                    .order_by(Match.round, Match.position, Match.id)
                ).all()

                athlete_ids = {
                    pid
                    for match in matches
                    for pid in (match.aka_id, match.ao_id)
                    if pid is not None
                }
                team_ids = {
                    pid
                    for match in matches
                    for pid in (match.aka_team_id, match.ao_team_id)
                    if pid is not None
                }
                tatami_ids = {
                    match.tatami_id
                    for match in matches
                    if match.tatami_id is not None
                }
                referee_ids = {
                    match.referee_id
                    for match in matches
                    if match.referee_id is not None
                }

                def _name_lookup(model: Any, ids: set[int]) -> dict[int, str]:
                    if not ids:
                        return {}
                    rows = session.exec(
                        select(model.id, model.name).where(
                            model.id.in_(sorted(ids))
                        )
                    ).all()
                    return {row[0]: row[1] for row in rows}

                athlete_names = _name_lookup(Athlete, athlete_ids)
                team_names = _name_lookup(Team, team_ids)
                tatami_names = _name_lookup(Tatami, tatami_ids)
                referee_names = _name_lookup(Referee, referee_ids)

            match_cards = build_match_cards(
                matches,
                athlete_names=athlete_names,
                team_names=team_names,
                tatami_names=tatami_names,
                referee_names=referee_names,
            )

            rounds = group_matches_by_round(match_cards)

            self.bracket_data = {
                "id": category.id,
                "name": category.name,
                "modality": category.modality,
                "competition_system": category.competition_system,
                "status": category.status,
                "rounds": rounds,
                "kata_flow_mode": getattr(category, "kata_flow_mode", "STANDARD"),
                "standings": [],
            }
        except Exception:
            logger.exception("Error loading category bracket")
            self.bracket_data = None
        finally:
            self.is_loading_bracket = False

    @rx.var
    def is_viewer_authenticated(self) -> bool:
        """Check if viewer code is valid and tournament loaded."""
        return self.current_tournament is not None and self.viewer_code != ""

    @rx.var
    def filtered_categories(self) -> list[dict[str, Any]]:
        """Computed categories for viewer listing."""
        return self.categories

    @rx.event
    def validate_tournament_access(self, tournament_id: int) -> Any:
        """Set access-denied state if viewer cannot access tournament."""
        self.access_denied = False
        if not self.is_viewer_authenticated:
            self.access_denied = True
            return rx.toast.error("Acceso no autorizado.")

        current_tournament_id = self.current_tournament.get("id")
        if current_tournament_id != tournament_id:
            self.access_denied = True
            return rx.toast.error("Acceso no autorizado a este torneo.")

        return rx.toast.success("Acceso autorizado")

    @rx.event
    async def load_viewer_dashboard(self) -> Any:
        """Load tournament from route param for dashboard on_load."""
        # Extract ?code= query param (critical gap fix)
        self.viewer_code = self.router.page.params.get("code", "")

        tournament_id = self.router.page.params.get("tournament_id")
        if tournament_id:
            return await self.load_tournament_by_id(int(tournament_id))
        return rx.redirect("/viewer")

    async def load_tournament_by_id(self, tournament_id: int) -> Any:
        """Load tournament by ID (for route parameter)."""
        with rx.session() as session:
            tournament = session.get(Tournament, tournament_id)
        if tournament and tournament.viewer_code == self.viewer_code:
            tournament_payload = tournament.model_dump(mode="json")
            tournament_payload["date"] = tournament_payload.get("start_date", "")
            self.current_tournament = tournament_payload
            self.access_denied = False
            await self.load_categories()
            return rx.toast.success("Torneo cargado")
        else:
            self.current_tournament = None
            self.access_denied = True
            return rx.toast.error("Acceso no autorizado a este torneo.")
