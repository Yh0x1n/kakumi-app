"""
KAKUMI - Tournament State
===========================
State de Reflex para gestión de transiciones de estado de torneos.
Expone event handlers semánticos para la UI y verifica RBAC antes de cada transición.

Patrón: sigue AuthState como referencia.
"""

from typing import Any, Optional

import reflex as rx
from sqlmodel import select

from kakumi_app.models.tournament_model import Tournament, TournamentStatus
from kakumi_app.services.tournament_service import TournamentService
from kakumi_app.services.auth_service import AuthService
from kakumi_app.states.auth_state import AuthState
from kakumi_app.states.tournament_category_state import TournamentCategoryState
from kakumi_app.states.tournament_tatami_state import TournamentTatamiState


# Rol mínimo requerido para gestionar estados de torneos
MANAGE_TOURNAMENT_STATUS_ROLE = "OPERATOR"


class TournamentState(rx.State):
    """
    State para gestión de transiciones de estado de torneos.

    Expone event handlers semánticos (open_registrations, start_competition, etc.)
    que validan RBAC antes de delegar al TournamentService.

    Variables de estado:
        current_tournament: Torneo actualmente seleccionado.
        transition_error: Mensaje de error de la última transición fallida.
        is_transitioning: True mientras se ejecuta una transición (UI feedback).
        validation_warnings: Lista de warnings de la última transición.
    """

    current_tournament: Optional[dict[str, Any]] = None
    tournaments: list[dict[str, Any]] = []
    transition_error: str = ""
    is_transitioning: bool = False
    validation_warnings: list[str] = []

    # ID del usuario actual (se setea desde AuthState)
    _current_user_id: int = 0
    _current_user_role: str = ""

    @rx.var
    def has_selected_tournament(self) -> bool:
        """Whether workspace currently has selected tournament."""
        return self.current_tournament is not None

    @rx.var
    def show_lifecycle_controls(self) -> bool:
        """Whether current user can see lifecycle workspace controls."""
        return AuthService.check_permission(
            self._current_user_role, MANAGE_TOURNAMENT_STATUS_ROLE
        )

    def _current_status(self) -> Optional[TournamentStatus]:
        """Return current tournament status as enum when available."""
        if not self.current_tournament:
            return None
        raw_status = self.current_tournament.get("status")
        if not raw_status:
            return None
        try:
            return TournamentStatus(str(raw_status))
        except ValueError:
            return None

    @staticmethod
    def _is_missing_workspace_state_error(exc: Exception) -> bool:
        """Ignore Reflex cache misses when optional workspace substates are absent."""
        return "is not cached and cannot be accessed without redis" in str(exc)

    def _can_show_transition(self, target_status: TournamentStatus) -> bool:
        """Whether workspace should expose given lifecycle action."""
        current_status = self._current_status()
        if not self.show_lifecycle_controls or current_status is None:
            return False
        return TournamentService.can_transition(current_status, target_status)

    @rx.var
    def show_open_registrations_action(self) -> bool:
        """Show PLANIFICADO -> INSCRIPCION action when valid."""
        return self._can_show_transition(TournamentStatus.INSCRIPCION)

    @rx.var
    def show_close_registrations_action(self) -> bool:
        """Show INSCRIPCION -> VERIFICACION action when valid."""
        return self._can_show_transition(TournamentStatus.VERIFICACION)

    @rx.var
    def show_start_competition_action(self) -> bool:
        """Show VERIFICACION -> EN_CURSO action when valid."""
        return self._can_show_transition(TournamentStatus.EN_CURSO)

    @rx.var
    def show_finish_competition_action(self) -> bool:
        """Show EN_CURSO -> FINALIZADO action when valid."""
        return self._can_show_transition(TournamentStatus.FINALIZADO)

    @rx.var
    def show_archive_tournament_action(self) -> bool:
        """Show FINALIZADO -> ARCHIVADO action when valid."""
        return self._can_show_transition(TournamentStatus.ARCHIVADO)

    @rx.var
    def show_reopen_registrations_action(self) -> bool:
        """Show INSCRIPCION -> PLANIFICADO action when valid."""
        return self._can_show_transition(TournamentStatus.PLANIFICADO)

    @rx.var
    def show_cancel_tournament_action(self) -> bool:
        """Show admin-only cancel action from PLANIFICADO."""
        current_status = self._current_status()
        if current_status != TournamentStatus.PLANIFICADO:
            return False
        return AuthService.check_permission(self._current_user_role, "ADMIN")

    @rx.event
    async def sync_auth_context(self) -> None:
        """Sync lifecycle auth context from AuthState session."""
        try:
            auth_state = await self.get_state(AuthState)
        except Exception:
            self._current_user_id = 0
            self._current_user_role = ""
            return

        # Apply dev auth bypass if env flag is active
        auth_state.refresh_auth()

        if not auth_state.is_authenticated or not auth_state.current_user:
            self._current_user_id = 0
            self._current_user_role = ""
            return

        self._current_user_id = int(auth_state.current_user.get("id", 0) or 0)
        self._current_user_role = str(auth_state.user_role or "")

    @rx.event
    async def load_workspace(self) -> None:
        """Load tournament workspace data and default selection."""
        await self.sync_auth_context()
        with rx.session() as session:
            tournaments = session.exec(select(Tournament).order_by(Tournament.id)).all()
            self.tournaments = [
                tournament.model_dump(mode="json") for tournament in tournaments
            ]

        if self.tournaments:
            await self.set_current_tournament(int(self.tournaments[0]["id"]))
        else:
            self.current_tournament = None
            self.transition_error = ""
            self.validation_warnings = []

    @rx.event
    async def set_current_tournament(self, tournament_id: int) -> None:
        """
        Cargar el torneo actual por ID desde la DB.

        Args:
            tournament_id: ID del torneo a cargar.
        """
        await self.refresh_current_tournament_snapshot(tournament_id)
        sync_errors: list[str] = []
        try:
            category_state = await self.get_state(TournamentCategoryState)
            await TournamentCategoryState.set_tournament_context.fn(
                category_state,
                tournament_id,
            )
        except Exception as exc:
            if self._is_missing_workspace_state_error(exc):
                category_state = None
            else:
                error_message = f"No se pudo sincronizar categorías del torneo: {exc}"
                sync_errors.append(error_message)
                self.transition_error = error_message
                rx.toast.error(error_message)
        try:
            tatami_state = await self.get_state(TournamentTatamiState)
            await TournamentTatamiState.set_tournament_context.fn(
                tatami_state,
                tournament_id,
            )
        except Exception as exc:
            if self._is_missing_workspace_state_error(exc):
                tatami_state = None
            else:
                error_message = f"No se pudo sincronizar tatamis del torneo: {exc}"
                sync_errors.append(error_message)
                self.transition_error = error_message
                rx.toast.error(error_message)
        await self.refresh_current_tournament_snapshot(tournament_id)
        self.transition_error = " | ".join(sync_errors)
        self.validation_warnings = []

    @rx.event
    async def refresh_current_tournament_snapshot(self, tournament_id: int) -> None:
        """Reload current tournament snapshot from persisted source of truth."""
        with rx.session() as session:
            tournament = session.get(Tournament, tournament_id)
            self.current_tournament = (
                tournament.model_dump(mode="json") if tournament else None
            )

    def _require_permission(self) -> bool:
        """
        Verificar permiso y setear error si no autorizado.

        Returns:
            True si autorizado, False si no.
        """
        if not AuthService.check_permission(
            self._current_user_role, MANAGE_TOURNAMENT_STATUS_ROLE
        ):
            self.transition_error = (
                "No tiene permisos para cambiar el estado del torneo. "
                f"Se requiere rol {MANAGE_TOURNAMENT_STATUS_ROLE} o superior."
            )
            return False
        return True

    def _get_tournament_id(self) -> Optional[int]:
        """
        Obtener el ID del torneo actual.

        Returns:
            ID del torneo o None si no hay torneo seleccionado.
        """
        if not self.current_tournament:
            self.transition_error = "No hay torneo seleccionado"
            return None
        tournament_id = self.current_tournament.get("id")
        return int(tournament_id) if tournament_id else None

    async def _execute_transition(self, new_status: TournamentStatus) -> None:
        """
        Ejecutar una transición de estado con validación RBAC y feedback UI.

        Args:
            new_status: Estado destino de la transición.
        """
        # Verificar permisos
        if not self._require_permission():
            return

        tournament_id = self._get_tournament_id()
        if tournament_id is None:
            return

        # Feedback de transición en progreso
        self.is_transitioning = True
        self.transition_error = ""
        self.validation_warnings = []

        result = TournamentService.transition_to(
            tournament_id=tournament_id,
            new_status=new_status,
            user_id=self._current_user_id,
        )

        self.is_transitioning = False

        if result.success:
            # Recargar el torneo desde DB para reflejar el nuevo estado
            await self.set_current_tournament(tournament_id)
            # Capturar warnings si existen
            self.validation_warnings = [w.message for w in result.warnings]
            if self.validation_warnings:
                yield rx.toast.warning(
                    "; ".join(self.validation_warnings), duration=5000
                )
            else:
                yield rx.toast.success(
                    f"Estado actualizado a {new_status.value}", duration=3000
                )
        else:
            self.transition_error = result.error_message or "Error desconocido"
            yield rx.toast.error(self.transition_error, duration=5000)

    @rx.event
    async def open_registrations(self) -> None:
        """
        PLANIFICADO → INSCRIPCION.
        Abre las inscripciones del torneo.
        """
        async for event in self._execute_transition(TournamentStatus.INSCRIPCION):
            yield event

    @rx.event
    async def close_registrations(self) -> None:
        """
        INSCRIPCION → VERIFICACION.
        Cierra inscripciones e inicia verificación de atletas.
        """
        async for event in self._execute_transition(TournamentStatus.VERIFICACION):
            yield event

    @rx.event
    async def start_competition(self) -> None:
        """
        VERIFICACION → EN_CURSO.
        Inicia la competencia activa del torneo.
        """
        async for event in self._execute_transition(TournamentStatus.EN_CURSO):
            yield event

    @rx.event
    async def finish_competition(self) -> None:
        """
        EN_CURSO → FINALIZADO.
        Finaliza la competencia del torneo.
        """
        async for event in self._execute_transition(TournamentStatus.FINALIZADO):
            yield event

    @rx.event
    async def archive_tournament(self) -> None:
        """
        FINALIZADO → ARCHIVADO.
        Archiva los resultados del torneo (también ADMIN: PLANIFICADO → ARCHIVADO).
        """
        async for event in self._execute_transition(TournamentStatus.ARCHIVADO):
            yield event

    @rx.event
    async def reopen_registrations(self) -> None:
        """
        INSCRIPCION → PLANIFICADO.
        Reabre las inscripciones (revierte cierre de inscripciones).
        """
        async for event in self._execute_transition(TournamentStatus.PLANIFICADO):
            yield event

    @rx.event
    async def cancel_tournament(self) -> None:
        """
        PLANIFICADO → ARCHIVADO (cancelar torneo — requiere ADMIN).
        """
        # Para cancelar torneo desde PLANIFICADO, requiere ADMIN
        if not AuthService.check_permission(self._current_user_role, "ADMIN"):
            self.transition_error = (
                "Solo administradores pueden cancelar un torneo en estado PLANIFICADO."
            )
            yield rx.toast.error(self.transition_error, duration=5000)
            return

        async for event in self._execute_transition(TournamentStatus.ARCHIVADO):
            yield event
