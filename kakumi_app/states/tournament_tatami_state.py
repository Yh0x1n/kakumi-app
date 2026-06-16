"""Tournament-scoped tatami CRUD state."""

from __future__ import annotations

from typing import Any, Optional

import reflex as rx
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from kakumi_app.models.tournament_model import Match, Tatami, Tournament


class TournamentTatamiState(rx.State):
    """Manage tatami rows for selected tournament workspace."""

    is_editing: bool = False
    show_form: bool = False
    error_message: str = ""
    search_query: str = ""
    current_page: int = 1
    page_size: int = 10

    current_tournament_id: int = 0
    current_tournament_name: str = ""
    tatamis: list[dict[str, Any]] = []
    current_tatami: Optional[dict[str, Any]] = None
    declared_tatami_count: int = 0
    active_tatami_count: int = 0

    name: str = ""
    location: str = ""


    def _set_form_open(self, editing: bool) -> None:
        """Open form with desired mode and clean inline errors."""
        self.is_editing = editing
        self.show_form = True
        self.error_message = ""

    def apply_search_query(self, value: str) -> None:
        """Normalize search value and reset pagination cursor."""
        self.search_query = value.strip()
        self.current_page = 1

    def paginate_rows(self, rows: list[dict]) -> list[dict]:
        """Return a deterministic page slice for in-memory rows."""
        if self.page_size <= 0:
            return rows
        start = max(self.current_page - 1, 0) * self.page_size
        end = start + self.page_size
        return rows[start:end]

    def reset_filters(self) -> None:
        """Reset default filter controls used by CRUD pages."""
        self.search_query = ""
        self.current_page = 1
    @rx.var
    def has_selected_tournament_context(self) -> bool:
        """Whether tatami workspace has selected tournament context."""
        return self.current_tournament_id > 0

    def set_name(self, value: str) -> None:
        """Set tatami name field."""
        self.name = value

    def set_location(self, value: str) -> None:
        """Set tatami location field."""
        self.location = value

    def reset_form(self) -> None:
        """Reset tatami form fields."""
        self.name = ""
        self.location = ""
        self.current_tatami = None

    def _serialize_tatami(self, tatami: Tatami) -> dict[str, Any]:
        """Return JSON-safe tatami row."""
        return {
            "id": tatami.id,
            "name": tatami.name,
            "location": tatami.location or "",
            "is_active": tatami.is_active,
            "current_match_id": tatami.current_match_id,
        }

    def _sync_tournament_mirror(self, session, tournament_id: int) -> int:
        """Persist tournament tatami_count from Tatami rows source of truth."""
        tatamis = session.exec(
            select(Tatami)
            .where(Tatami.tournament_id == tournament_id)
            .order_by(Tatami.id)
        ).all()
        declared_count = len(tatamis)
        tournament = session.get(Tournament, tournament_id)
        if tournament and tournament.tatami_count != declared_count:
            tournament.tatami_count = declared_count
            session.add(tournament)
            session.commit()
        return declared_count

    def _refresh_tatamis(self, session) -> None:
        """Reload tatami rows and derived counters for current tournament."""
        if not self.current_tournament_id:
            self.tatamis = []
            self.declared_tatami_count = 0
            self.active_tatami_count = 0
            return

        tatamis = session.exec(
            select(Tatami)
            .where(Tatami.tournament_id == self.current_tournament_id)
            .order_by(Tatami.id)
        ).all()
        self.tatamis = [self._serialize_tatami(tatami) for tatami in tatamis]
        self.declared_tatami_count = len(tatamis)
        self.active_tatami_count = sum(1 for tatami in tatamis if tatami.is_active)

    async def _sync_workspace_summary(self) -> None:
        """Refresh TournamentState summary after tatami mutations."""
        if not self.current_tournament_id:
            return

        try:
            from kakumi_app.states.tournament_state import TournamentState

            tournament_state = await self.get_state(TournamentState)
            await TournamentState.refresh_current_tournament_snapshot.fn(
                tournament_state,
                self.current_tournament_id,
            )
        except Exception:
            return

    @rx.event
    async def set_tournament_context(self, tournament_id: int) -> None:
        """Bind tatami workspace to selected tournament and repair mirror drift."""
        with rx.session() as session:
            tournament = session.get(Tournament, tournament_id)
            if tournament is None:
                self.current_tournament_id = 0
                self.current_tournament_name = ""
                self.tatamis = []
                self.declared_tatami_count = 0
                self.active_tatami_count = 0
                self.error_message = "Torneo no encontrado"
                self.show_form = False
                self.current_tatami = None
                return

            self.current_tournament_id = tournament.id
            self.current_tournament_name = tournament.name
            self.error_message = ""
            self.show_form = False
            self.reset_form()
            self._sync_tournament_mirror(session, tournament.id)
            self._refresh_tatamis(session)

        await self._sync_workspace_summary()

    def set_form_values(
        self,
        _: Any,
        tatami: Optional[dict[str, Any]] = None,
    ) -> None:
        """Open form in create or edit mode."""
        if tatami:
            self.current_tatami = tatami
            self._set_form_open(editing=True)
            self.name = tatami.get("name", "")
            self.location = tatami.get("location", "")
            return

        self.reset_form()
        self._set_form_open(editing=False)

    @rx.event
    def cancel_tatami_form(self) -> None:
        """Close tatami form and clear transient errors."""
        self.show_form = False
        self.error_message = ""

    def _validate_form(self) -> Optional[dict[str, Any]]:
        """Validate tatami payload before DB writes."""
        if not self.current_tournament_id:
            self.error_message = "Selecciona un torneo primero"
            return None

        if not self.name.strip():
            self.error_message = "Nombre tatami es obligatorio"
            return None

        self.error_message = ""
        return {
            "name": self.name.strip(),
            "location": self.location.strip() or None,
            "tournament_id": self.current_tournament_id,
        }

    @rx.event
    async def save_tatami(self) -> Any:
        """Create or update tatami row and keep tournament mirror synchronized."""
        tatami_data = self._validate_form()
        if tatami_data is None:
            return None

        with rx.session() as session:
            try:
                if self.is_editing and self.current_tatami:
                    tatami_id = self.current_tatami.get("id")
                    tatami = session.get(Tatami, int(tatami_id)) if tatami_id else None
                    if tatami is None:
                        self.error_message = "Tatami no encontrado"
                        return rx.toast.error(self.error_message)

                    tatami.name = str(tatami_data["name"])
                    tatami.location = tatami_data["location"]
                    session.add(tatami)
                    session.commit()
                    message = f"Tatami '{tatami.name}' actualizado"
                else:
                    tatami = Tatami(**tatami_data)
                    session.add(tatami)
                    session.commit()
                    session.refresh(tatami)
                    message = f"Tatami '{tatami.name}' creado"

                self._sync_tournament_mirror(session, self.current_tournament_id)
                self._refresh_tatamis(session)
            except SQLAlchemyError:
                session.rollback()
                self.error_message = "Error al guardar tatami"
                return rx.toast.error(self.error_message)

        self.show_form = False
        self.reset_form()
        await self._sync_workspace_summary()
        return rx.toast.success(message)

    @rx.event
    async def toggle_tatami_active(self, tatami_id: int) -> Any:
        """Toggle tatami availability without changing declared row count."""
        with rx.session() as session:
            tatami = session.get(Tatami, tatami_id)
            if tatami is None:
                return rx.toast.error("Tatami no encontrado")

            try:
                tatami.is_active = not tatami.is_active
                session.add(tatami)
                session.commit()
                self._sync_tournament_mirror(session, tatami.tournament_id)
                self._refresh_tatamis(session)
            except SQLAlchemyError:
                session.rollback()
                self.error_message = "Error al actualizar tatami"
                return rx.toast.error(self.error_message)

        self.error_message = ""
        await self._sync_workspace_summary()
        action = "activado" if tatami.is_active else "desactivado"
        return rx.toast.success(f"Tatami '{tatami.name}' {action}")

    @rx.event
    async def delete_tatami(self, tatami_id: int) -> Any:
        """Delete tatami only when no match assignment depends on it."""
        with rx.session() as session:
            tatami = session.get(Tatami, tatami_id)
            if tatami is None:
                return rx.toast.error("Tatami no encontrado")

            if tatami.tournament_id != self.current_tournament_id:
                self.error_message = "Tatami fuera del torneo seleccionado"
                return rx.toast.error(self.error_message)

            has_assigned_matches = session.exec(
                select(Match.id).where(Match.tatami_id == tatami_id)
            ).first()
            if tatami.current_match_id or has_assigned_matches:
                self.error_message = (
                    "No se puede eliminar tatami con encuentro actual asignado"
                )
                return None

            tatami_name = tatami.name
            try:
                session.delete(tatami)
                session.commit()
                self._sync_tournament_mirror(session, self.current_tournament_id)
                self._refresh_tatamis(session)
            except SQLAlchemyError:
                session.rollback()
                self.error_message = "Error al eliminar tatami"
                return rx.toast.error(self.error_message)

        self.error_message = ""
        await self._sync_workspace_summary()
        return rx.toast.success(f"Tatami '{tatami_name}' eliminado")
