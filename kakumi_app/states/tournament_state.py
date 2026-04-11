"""
KAKUMI - Tournament State
===========================
State de Reflex para gestión de transiciones de estado de torneos.
Expone event handlers semánticos para la UI y verifica RBAC antes de cada transición.

Patrón: sigue AuthState como referencia.
"""

from typing import Optional

import reflex as rx

from kakumi_app.models.tournament_model import Tournament, TournamentStatus
from kakumi_app.services.tournament_service import TournamentService
from kakumi_app.services.auth_service import AuthService


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

    current_tournament: Optional[Tournament] = None
    transition_error: str = ""
    is_transitioning: bool = False
    validation_warnings: list[str] = []

    # ID del usuario actual (se setea desde AuthState)
    _current_user_id: int = 0
    _current_user_role: str = ""

    def set_current_tournament(self, tournament_id: int) -> None:
        """
        Cargar el torneo actual por ID desde la DB.

        Args:
            tournament_id: ID del torneo a cargar.
        """
        with rx.session() as session:
            self.current_tournament = session.get(Tournament, tournament_id)
        self.transition_error = ""
        self.validation_warnings = []

    def _check_permission(self) -> bool:
        """
        Verificar que el usuario actual tiene permiso para gestionar estados.

        Returns:
            True si autorizado, False si no tiene permiso.
        """
        return AuthService.check_permission(
            self._current_user_role, MANAGE_TOURNAMENT_STATUS_ROLE
        )

    def _require_permission(self) -> bool:
        """
        Verificar permiso y setear error si no autorizado.

        Returns:
            True si autorizado, False si no.
        """
        if not self._check_permission():
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
        return self.current_tournament.id

    def _execute_transition(self, new_status: TournamentStatus) -> None:
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
            self.set_current_tournament(tournament_id)
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

    def open_registrations(self) -> None:
        """
        PLANIFICADO → INSCRIPCION.
        Abre las inscripciones del torneo.
        """
        yield from self._execute_transition(TournamentStatus.INSCRIPCION)

    def close_registrations(self) -> None:
        """
        INSCRIPCION → VERIFICACION.
        Cierra inscripciones e inicia verificación de atletas.
        """
        yield from self._execute_transition(TournamentStatus.VERIFICACION)

    def start_competition(self) -> None:
        """
        VERIFICACION → EN_CURSO.
        Inicia la competencia activa del torneo.
        """
        yield from self._execute_transition(TournamentStatus.EN_CURSO)

    def finish_competition(self) -> None:
        """
        EN_CURSO → FINALIZADO.
        Finaliza la competencia del torneo.
        """
        yield from self._execute_transition(TournamentStatus.FINALIZADO)

    def archive_tournament(self) -> None:
        """
        FINALIZADO → ARCHIVADO.
        Archiva los resultados del torneo (también ADMIN: PLANIFICADO → ARCHIVADO).
        """
        yield from self._execute_transition(TournamentStatus.ARCHIVADO)

    def reopen_registrations(self) -> None:
        """
        INSCRIPCION → PLANIFICADO.
        Reabre las inscripciones (revierte cierre de inscripciones).
        """
        yield from self._execute_transition(TournamentStatus.PLANIFICADO)

    def cancel_tournament(self) -> None:
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

        yield from self._execute_transition(TournamentStatus.ARCHIVADO)
