"""
Tournament State
Reflex state for tournament management.
"""

import datetime
from typing import Dict, List, Optional

import reflex as rx

from kakumi_app.models.tournament_model import Tournament, TournamentStatus
from kakumi_app.services.tournament_service import TournamentService


class TournamentState(rx.State):
    """State for tournament list and current tournament."""

    tournaments: List[Tournament] = []
    current_tournament: Optional[Tournament] = None
    loading: bool = False
    error: Optional[str] = None

    # Form fields for creating/editing tournament
    form_name: str = ""
    form_date: str = ""

    @rx.var
    def tournament_count(self) -> int:
        return len(self.tournaments)

    def load_tournaments(self):
        """Load all tournaments."""
        self.loading = True
        self.error = None
        try:
            self.tournaments = TournamentService.get_all_tournaments()
        except Exception as e:
            self.error = str(e)
        finally:
            self.loading = False

    def select_tournament(self, tournament_id: int):
        """Select a tournament by ID."""
        self.current_tournament = TournamentService.get_tournament_by_id(tournament_id)
        self.clear_form()

    def clear_form(self):
        """Clear form fields."""
        self.form_name = ""
        self.form_date = ""

    def populate_form_from_tournament(self, tournament: Tournament):
        """Populate form with tournament data."""
        self.form_name = tournament.name
        self.form_date = tournament.date.isoformat() if tournament.date else ""

    @rx.event
    def create_tournament(self):
        """Create a new tournament."""
        try:
            date = (
                datetime.date.fromisoformat(self.form_date)
                if self.form_date
                else datetime.date.today()
            )
            tournament = TournamentService.create_tournament(
                name=self.form_name,
                date=date,
            )
            self.tournaments.append(tournament)
            self.current_tournament = tournament
            self.clear_form()
            yield rx.toast.success("Tournament created successfully.")
        except Exception as e:
            yield rx.toast.error(f"Failed to create tournament: {e}")

    @rx.event
    def update_tournament(self):
        """Update the current tournament."""
        if not self.current_tournament:
            yield rx.toast.error("No tournament selected.")
            return
        updates = {}
        if self.form_name:
            updates["name"] = self.form_name
        if self.form_date:
            updates["date"] = datetime.date.fromisoformat(self.form_date)

        tournament = TournamentService.update_tournament(
            self.current_tournament.id, updates
        )
        if tournament:
            self.current_tournament = tournament
            # Update tournament in list
            for i, t in enumerate(self.tournaments):
                if t.id == tournament.id:
                    self.tournaments[i] = tournament
                    break
            self.clear_form()
            yield rx.toast.success("Tournament updated.")
        else:
            yield rx.toast.error("Failed to update tournament.")

    @rx.event
    def delete_tournament(self, tournament_id: int):
        """Delete a tournament."""
        success = TournamentService.delete_tournament(tournament_id)
        if success:
            self.tournaments = [t for t in self.tournaments if t.id != tournament_id]
            if self.current_tournament and self.current_tournament.id == tournament_id:
                self.current_tournament = None
            yield rx.toast.success("Tournament deleted.")
        else:
            yield rx.toast.error("Failed to delete tournament.")

    @rx.event
    def change_status(self, new_status_str: str):
        """Change tournament status."""
        if not self.current_tournament:
            yield rx.toast.error("No tournament selected.")
            return
        try:
            new_status = TournamentStatus(new_status_str)
        except ValueError:
            yield rx.toast.error("Invalid status.")
            return
        tournament, error = TournamentService.change_tournament_status(
            self.current_tournament.id, new_status
        )
        if tournament:
            self.current_tournament = tournament
            # Update list
            for i, t in enumerate(self.tournaments):
                if t.id == tournament.id:
                    self.tournaments[i] = tournament
                    break
            yield rx.toast.success(f"Status changed to {new_status.value}.")
        else:
            yield rx.toast.error(error)

    @rx.event
    def open_inscriptions(self):
        """Open inscriptions for current tournament."""
        self.change_status(TournamentStatus.INSCRIPCION.value)

    @rx.event
    def close_inscriptions(self):
        """Close inscriptions."""
        self.change_status(TournamentStatus.VERIFICACION.value)

    @rx.event
    def start_competition(self):
        """Start competition."""
        self.change_status(TournamentStatus.EN_CURSO.value)

    @rx.event
    def finish_tournament(self):
        """Finish tournament."""
        self.change_status(TournamentStatus.FINALIZADO.value)

    @rx.event
    def archive_tournament(self):
        """Archive tournament."""
        self.change_status(TournamentStatus.ARCHIVADO.value)

    @rx.event
    def reset_tournament(self):
        """Reset tournament to planned."""
        self.change_status(TournamentStatus.PLANIFICADO.value)
