"""
Viewer State
Manages viewer code validation and access to tournament data.
"""

from typing import Optional, List, Dict, Any

import reflex as rx

from kakumi_app.models.tournament_model import Tournament
from kakumi_app.services.viewer_service import ViewerService


class ViewerState(rx.State):
    """State for viewer access management."""

    # Viewer code stored locally
    viewer_code: str = rx.LocalStorage()

    # Current tournament (if code valid)
    current_tournament: Optional[Tournament] = None

    # Categories for the tournament (list of dicts)
    categories: List[Dict[str, Any]] = []

    # Selected category for bracket/live view
    selected_category_id: Optional[int] = None
    selected_category_type: Optional[str] = None  # "kata" or "kumite"

    # UI state
    error_message: str = ""
    is_loading: bool = False

    @rx.event
    def set_viewer_code(self, code: str):
        """Set the viewer code from input."""
        self.viewer_code = code

    @rx.event
    async def validate_and_load_tournament(self):
        """Validate the viewer code and load the associated tournament."""
        self.is_loading = True
        self.error_message = ""

        if not self.viewer_code:
            self.error_message = "Por favor ingrese un código de espectador."
            self.is_loading = False
            return

        tournament = ViewerService.validate_viewer_code(self.viewer_code)
        if tournament:
            self.current_tournament = tournament
            self.error_message = ""
            await self.load_categories()
        else:
            self.current_tournament = None
            self.error_message = "Código de espectador inválido."

        self.is_loading = False

    @rx.event
    def clear_viewer_session(self):
        """Clear viewer session (logout)."""
        self.viewer_code = ""
        self.current_tournament = None
        self.categories = []
        self.selected_category_id = None
        self.selected_category_type = None
        self.error_message = ""

    @rx.event
    async def load_categories(self):
        """Load categories from current tournament."""
        self.categories = []
        if not self.current_tournament:
            return
        # Kata categories
        for cat in self.current_tournament.kata_categories:
            self.categories.append(
                {
                    "id": cat.id,
                    "name": cat.name,
                    "type": "kata",
                }
            )
        # Kumite categories
        for cat in self.current_tournament.kumite_categories:
            self.categories.append(
                {
                    "id": cat.id,
                    "name": cat.name,
                    "type": "kumite",
                }
            )

    @rx.event
    def select_category(self, category_id: int, category_type: str):
        """Select a category for viewing bracket and live match."""
        self.selected_category_id = category_id
        self.selected_category_type = category_type

    @rx.var
    def is_viewer_authenticated(self) -> bool:
        """Check if viewer code is valid and tournament loaded."""
        return self.current_tournament is not None and self.viewer_code != ""

    @rx.var
    def filtered_categories(self) -> list[dict]:
        """Computed categories for viewer listing."""
        return self.categories

    @rx.event
    def validate_tournament_access(self, tournament_id: int) -> bool:
        """Check if the current viewer code grants access to the given tournament."""
        if not self.is_viewer_authenticated:
            return False
        return self.current_tournament.id == tournament_id

    @rx.event
    async def load_tournament_by_id(self, tournament_id: int):
        """Load tournament by ID (for route parameter)."""
        from kakumi_app.services.tournament_service import TournamentService

        tournament = TournamentService.get_tournament_by_id(tournament_id)
        if tournament and tournament.viewer_code == self.viewer_code:
            self.current_tournament = tournament
        else:
            self.current_tournament = None
            self.error_message = "Acceso no autorizado a este torneo."
