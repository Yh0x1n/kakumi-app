"""Tournament CRUD state used by registries pages."""

from __future__ import annotations

import datetime
from typing import Any, Optional

import reflex as rx
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from kakumi_app.models.tournament_model import (
    Match,
    Tatami,
    Tournament,
    TournamentCategory,
    TournamentStatus,
)
from kakumi_app.states.base_crud_state import CrudStateMixin


class TournamentCrudState(CrudStateMixin, rx.State):
    """State for tournament CRUD screens in registries module."""

    is_editing: bool = CrudStateMixin.is_editing
    show_form: bool = CrudStateMixin.show_form
    error_message: str = CrudStateMixin.error_message
    search_query: str = CrudStateMixin.search_query

    tournaments: list[dict[str, Any]] = []
    current_tournament: Optional[dict[str, Any]] = None

    name: str = ""
    venue: str = ""
    start_date: str = ""
    end_date: str = ""
    tatami_count: str = "1"
    status: str = TournamentStatus.PLANIFICADO.value
    created_by_id: str = ""

    status_options: list[str] = [status.value for status in TournamentStatus]

    def _serialize_tournament(self, tournament: Tournament) -> dict[str, Any]:
        """Return JSON-safe tournament row for CRUD list and edit flow."""
        return {
            "id": tournament.id,
            "name": tournament.name,
            "venue": tournament.venue,
            "status": tournament.status,
            "start_date": tournament.start_date.isoformat(),
            "end_date": tournament.end_date.isoformat(),
            "tatami_count": tournament.tatami_count,
            "created_by_id": tournament.created_by_id,
        }

    @rx.event
    async def initialize_registry_view(self) -> None:
        """Initialize tournament registries page state."""
        self.show_form = False
        self.error_message = ""
        self.search_query = ""
        await self.load_tournaments()

    @rx.event
    async def load_tournaments(self) -> None:
        """Load all tournaments from database."""
        with rx.session() as session:
            tournaments = session.exec(select(Tournament)).all()
            self.tournaments = [
                self._serialize_tournament(tournament) for tournament in tournaments
            ]

    @rx.event
    async def filter_tournaments(self) -> None:
        """Filter tournaments by name, venue, or status."""
        if not self.search_query:
            await self.load_tournaments()
            return

        query = self.search_query.lower()
        with rx.session() as session:
            tournaments = session.exec(select(Tournament)).all()
            self.tournaments = [
                self._serialize_tournament(tournament)
                for tournament in tournaments
                if query in tournament.name.lower()
                or query in tournament.venue.lower()
                or query in tournament.status.lower()
            ]

    @rx.event
    def set_form_values(
        self,
        _: Any,
        tournament: Optional[dict[str, Any]] = None,
    ) -> None:
        """Set form values for edit or create modes."""
        if tournament:
            self.current_tournament = tournament
            self._set_form_open(editing=True)
            self.name = tournament.get("name", "")
            self.venue = tournament.get("venue", "")
            self.start_date = tournament.get("start_date", "")
            self.end_date = tournament.get("end_date") or self.start_date
            self.tatami_count = str(tournament.get("tatami_count") or "1")
            self.status = tournament.get("status", TournamentStatus.PLANIFICADO.value)
            created_by_id = tournament.get("created_by_id")
            self.created_by_id = str(created_by_id) if created_by_id else ""
            return

        self.current_tournament = None
        self._set_form_open(editing=False)
        self.reset_form()

    def reset_form(self) -> None:
        """Reset form fields to defaults."""
        self.name = ""
        self.venue = ""
        self.start_date = ""
        self.end_date = ""
        self.tatami_count = "1"
        self.status = TournamentStatus.PLANIFICADO.value
        self.created_by_id = ""

    def _validate_form(self) -> bool:
        """Validate required tournament form fields."""
        if not self.name.strip():
            self.error_message = "Name is required"
            return False

        if not self.venue.strip():
            self.error_message = "Venue is required"
            return False

        if not self.start_date or not self.end_date:
            self.error_message = "Start and end dates are required"
            return False

        if self.status not in self.status_options:
            self.error_message = "Invalid tournament status"
            return False

        return True

    @rx.event
    async def save_tournament(self) -> Any:  # noqa: C901
        """Create or update tournament."""
        if not self._validate_form():
            return

        try:
            start_date = datetime.datetime.strptime(self.start_date, "%Y-%m-%d").date()
            end_date = datetime.datetime.strptime(self.end_date, "%Y-%m-%d").date()
        except ValueError:
            self.error_message = "Invalid date format (YYYY-MM-DD)"
            return

        try:
            tatami_count = int(self.tatami_count) if self.tatami_count else 1
        except ValueError:
            self.error_message = "Tatami count must be a number"
            return

        created_by_id: Optional[int] = None
        if self.created_by_id:
            try:
                created_by_id = int(self.created_by_id)
            except ValueError:
                self.error_message = "Creator ID must be a number"
                return

        tournament_data = {
            "name": self.name.strip(),
            "venue": self.venue.strip(),
            "start_date": start_date,
            "end_date": end_date,
            "tatami_count": tatami_count,
            "created_by_id": created_by_id,
        }

        with rx.session() as session:
            if self.is_editing and self.current_tournament:
                tournament_id = self.current_tournament.get("id")
                tournament = (
                    session.get(Tournament, int(tournament_id))
                    if tournament_id
                    else None
                )
                if not tournament:
                    return rx.toast.error("Tournament not found")

                try:
                    tournament_data["status"] = tournament.status
                    for key, value in tournament_data.items():
                        setattr(tournament, key, value)

                    session.add(tournament)
                    session.commit()
                    success_message = (
                        f"Tournament '{tournament.name}' updated successfully"
                    )
                except SQLAlchemyError:
                    session.rollback()
                    self.error_message = "Error al guardar torneo"
                    return rx.toast.error(self.error_message)
            else:
                try:
                    existing = session.exec(
                        select(Tournament).where(Tournament.name == self.name.strip())
                    ).first()
                    if existing:
                        return rx.toast.error(
                            f"Tournament with name '{self.name}' already exists"
                        )

                    tournament = Tournament(
                        **tournament_data,
                        status=TournamentStatus.PLANIFICADO.value,
                    )
                    session.add(tournament)
                    session.commit()
                    success_message = (
                        f"Tournament '{tournament.name}' created successfully"
                    )
                except SQLAlchemyError:
                    session.rollback()
                    self.error_message = "Error al guardar torneo"
                    return rx.toast.error(self.error_message)

        self.show_form = False
        await self.load_tournaments()
        return rx.toast.success(success_message)

    @rx.event
    async def delete_tournament(self, tournament_id: int) -> Any:
        """Delete tournament when it has no dependent records."""
        with rx.session() as session:
            tournament = session.get(Tournament, tournament_id)
            if not tournament:
                return rx.toast.error("Tournament not found")

            if tournament.status != TournamentStatus.PLANIFICADO.value:
                self.error_message = (
                    f"No se puede eliminar torneo en estado {tournament.status}"
                )
                return rx.toast.error(self.error_message)

            has_categories = session.exec(
                select(TournamentCategory.id).where(
                    TournamentCategory.tournament_id == tournament_id
                )
            ).first()
            has_matches = session.exec(
                select(Match.id).where(Match.tournament_id == tournament_id)
            ).first()
            has_tatamis = session.exec(
                select(Tatami.id).where(Tatami.tournament_id == tournament_id)
            ).first()

            if has_categories or has_matches or has_tatamis:
                self.error_message = (
                    "No se puede eliminar torneo con categorías, matches o tatamis "
                    "relacionados"
                )
                return rx.toast.error(self.error_message)

            tournament_name = tournament.name
            session.delete(tournament)
            session.commit()

        await self.load_tournaments()
        return rx.toast.success(f"Tournament '{tournament_name}' deleted")

    @rx.event
    def cancel_form(self) -> None:
        """Cancel tournament form using shared mixin behavior."""
        CrudStateMixin.cancel_form(self)
