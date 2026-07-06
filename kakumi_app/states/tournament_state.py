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
from kakumi_app.states.tournament_crud_state import TournamentCrudState
from kakumi_app.states.tournament_tatami_state import TournamentTatamiState
import datetime
from kakumi_app.services.viewer_service import ViewerService
from kakumi_app.services.qr_helper import _make_qr_data_url


# Rol mínimo requerido para gestionar estados de torneos
MANAGE_TOURNAMENT_STATUS_ROLE = "OPERATOR"

# ── Step machine constants (must match rx.match slots in tournament.py) ──
SELECTION_STEP = 0
STATUS_STEP = 1
FORM_STEP = 2
CATEGORIES_STEP = 3
TATAMIS_STEP = 4
CONFIRM_STEP = 5
EDIT_CHOICE_STEP = 6


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

    # ── QR state vars ──────────────────────────────────
    qr_data_url: str = ""
    qr_code_text: str = ""
    qr_generated_at: str = ""
    qr_expires_at: str = ""
    qr_viewer_url: str = ""

    # ID del usuario actual (se setea desde AuthState)
    _current_user_id: int = 0
    _current_user_role: str = ""

    # ── Step machine vars ──────────────────────────────
    step_index: int = 0
    create_mode: bool = False
    edit_mode: bool = False
    _step_count: int = 7
    _form_saved_tournament_id: int = 0

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

    # ── Transition validation ─────────────────────────

    def _validate_step_transition(self, from_step: int, to_step: int) -> bool:
        """Validates step transitions. Returns True if allowed.

        Normal: adjacent steps always allowed within [0, _step_count-1].
        Special: create/edit flow shortcuts gated by mode flags.
        """
        if to_step >= 1 and not self.has_selected_tournament and to_step not in (0, 6):
            return False
        if abs(to_step - from_step) == 1:
            return 0 <= to_step < self._step_count
        special = {
            (0, 2): self.create_mode,
            (0, 6): self.edit_mode,
            (0, 3): self.edit_mode,
            (2, 0): not self.create_mode,
            (2, 1): not self.create_mode,
            (3, 1): self.edit_mode,
            (3, 2): False,
            (5, 1): True,
            (2, 3): self.create_mode,
            (3, 4): self.create_mode,
            (4, 5): self.create_mode,
            (6, 2): self.edit_mode,
            (6, 3): self.edit_mode,
            (6, 1): self.edit_mode,
            (6, 0): self.edit_mode,
        }
        return special.get((from_step, to_step), False)

    # ── Navigation handlers ───────────────────────────

    @rx.event
    def go_next(self) -> None:
        """Advance one step. Guards via can_go_next."""
        if not self.can_go_next:
            return
        self.step_index += 1

    @rx.event
    def go_previous(self) -> None:
        """Go back one step. Guards via can_go_previous.
        
        Special case: in create flow, going back from form (step 2)
        returns to selection (step 0) and exits create mode.
        """
        if not self.can_go_previous:
            return
        if self.create_mode and self.step_index == FORM_STEP:
            self.step_index = SELECTION_STEP
            self.create_mode = False
        else:
            self.step_index -= 1

    @rx.event
    def go_to_step(self, target_step: int) -> None:
        """Non-sequential jump (create/edit shortcuts). Validated via transition map."""
        if not self._validate_step_transition(self.step_index, target_step):
            return
        self.step_index = target_step

    # ── Flow handlers ─────────────────────────────────

    @rx.event
    async def start_create_flow(self) -> None:
        """Start create tournament flow. Jump to form step."""
        self.create_mode = True
        self.edit_mode = False
        try:
            crud = await self.get_state(TournamentCrudState)
            crud.set_form_values(None, None)
        except Exception:
            pass
        self.go_to_step(FORM_STEP)

    @rx.event
    async def start_edit_flow(self) -> None:
        """Start edit tournament flow. Jump based on status."""
        if not self.current_tournament:
            yield rx.toast.error("Selecciona torneo primero")
            return
        self.edit_mode = True
        self.create_mode = False
        status = self._current_status()
        if status == TournamentStatus.PLANIFICADO:
            self.go_to_step(EDIT_CHOICE_STEP)
        elif self.is_readonly_mode:
            self.go_to_step(CATEGORIES_STEP)
        else:
            self.go_to_step(STATUS_STEP)

    @rx.event
    async def complete_create_flow(self) -> None:
        """Finish create flow: transition tournament to EN_CURSO."""
        tournament_id = self._get_tournament_id()
        if tournament_id is None:
            yield rx.toast.error("No hay torneo seleccionado")
            return
        async for event in self._execute_transition(TournamentStatus.EN_CURSO):
            yield event
        if not self.transition_error:
            self.create_mode = False
            self.go_to_step(STATUS_STEP)

    @rx.event
    async def advance_after_form_saved(self) -> None:
        """Advance after form save: categories (create) or status (edit)."""
        if self.create_mode:
            self.go_to_step(CATEGORIES_STEP)
        else:
            self.go_to_step(STATUS_STEP)

    @rx.event
    def cancel_create_flow(self) -> None:
        """Cancel create flow: reset mode, go back to selection."""
        self.create_mode = False
        self.edit_mode = False
        self.step_index = SELECTION_STEP

    # ── Bridge: TournamentCrudState coordinator ───────

    @rx.event
    async def handle_form_submit(self) -> None:
        """Bridge: delegates to TournamentCrudState.save_tournament, advances on success."""
        crud = await self.get_state(TournamentCrudState)
        await crud.save_tournament()
        if not crud.show_form and not crud.error_message:
            self._form_saved_tournament_id = (
                crud.current_tournament.get("id", 0) if crud.current_tournament else 0
            )
            await self.advance_after_form_saved()

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

    # ── Step machine computed guards ───────────────────

    @rx.var
    def can_go_next(self) -> bool:
        """Whether 'Siguiente' button is enabled."""
        if self.step_index >= self._step_count - 1:
            return False
        if self.step_index == 0 and not self.has_selected_tournament:
            return False
        status = self._current_status()
        if status == TournamentStatus.ARCHIVADO and self.step_index > 0:
            return False
        return self._validate_step_transition(self.step_index, self.step_index + 1)

    @rx.var
    def can_go_previous(self) -> bool:
        """Whether 'Anterior' button is enabled."""
        return self.step_index > 0

    @rx.var
    def is_readonly_mode(self) -> bool:
        """Cards render readonly when tournament is in advanced state."""
        if not self.current_tournament:
            return False
        status = self._current_status()
        if not status:
            return False
        advanced = {
            TournamentStatus.INSCRIPCION,
            TournamentStatus.VERIFICACION,
            TournamentStatus.EN_CURSO,
            TournamentStatus.FINALIZADO,
            TournamentStatus.ARCHIVADO,
        }
        return status in advanced

    @rx.var
    def _step_labels(self) -> list[str]:
        """Dynamic step labels based on create/edit mode."""
        if self.create_mode:
            return [
                "Seleccion", "Estado", "Formulario",
                "Categorias", "Tatamis", "Confirmar",
            ]
        if self.edit_mode:
            return [
                "Seleccion", "Estado", "Editar",
                "Categorias", "Tatamis",
            ]
        return [
            "Seleccion", "Estado",
            "Categorias", "Tatamis",
        ]

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
        # Reset step machine
        self.step_index = 0
        self.create_mode = False
        self.edit_mode = False
        self._form_saved_tournament_id = 0
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
            self._clear_qr_vars()

    def _clear_qr_vars(self) -> None:
        """Reset all QR-related state vars to empty strings."""
        self.qr_data_url = ""
        self.qr_code_text = ""
        self.qr_generated_at = ""
        self.qr_expires_at = ""
        self.qr_viewer_url = ""

    @rx.event

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

        # Clear QR state vars when switching to a different tournament
        # to avoid showing stale QR data from a previous tournament
        self._clear_qr_vars()

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
            self.validation_warnings = list(result.warnings)
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

    # ── Base URL helper ───────────────────────────────

    @staticmethod
    def _resolve_base_url(router) -> str:
        """Extract base URL from router data (pure function, no self).

        Priority:
          1. router.url.origin (if it has an 'origin' attribute)
          2. X-Forwarded-Proto + X-Forwarded-Host (reverse proxy headers)
          3. Host header fallback with http://
        """
        try:
            if hasattr(router, "url") and getattr(router.url, "origin", None):
                return router.url.origin
        except AttributeError:
            pass

        scheme = "http"
        host = router.headers.get("host", "localhost:3000")

        try:
            raw = router.headers.raw_headers
            if b"x-forwarded-proto" in raw:
                proto_value = raw[b"x-forwarded-proto"]
                if proto_value and len(proto_value) > 0:
                    scheme = proto_value[0].decode("utf-8", errors="replace")
            if b"x-forwarded-host" in raw:
                host_value = raw[b"x-forwarded-host"]
                if host_value and len(host_value) > 0:
                    host = host_value[0].decode("utf-8", errors="replace")
        except (AttributeError, KeyError, IndexError):
            pass

        return f"{scheme}://{host}"

    def _get_base_url(self) -> str:
        """Extract base URL from router context for QR generation."""
        return self._resolve_base_url(self.router)

    # ── QR event handlers ──────────────────────────

    @rx.event
    async def generate_qr(self) -> None:
        """Generate viewer code + QR for current tournament."""
        tournament_id = self._get_tournament_id()
        if tournament_id is None:
            yield rx.toast.error("No tournament selected")
            return

        code = ViewerService.generate_viewer_code(tournament_id)
        if code is None:
            yield rx.toast.error("Could not generate viewer code")
            return

        # Build absolute URL from router context (QR scan from other devices)
        base_url = self._get_base_url()
        url = f"{base_url}/viewer/dashboard/{tournament_id}?code={code}"
        data_uri = _make_qr_data_url(url)

        now = datetime.datetime.now(tz=datetime.UTC)
        expires = now + datetime.timedelta(hours=5)

        self.qr_data_url = data_uri
        self.qr_code_text = code
        self.qr_viewer_url = url
        self.qr_generated_at = now.strftime("%Y-%m-%d %H:%M UTC")
        self.qr_expires_at = expires.strftime("%Y-%m-%d %H:%M UTC")

        yield rx.toast.success("QR generado")

    @rx.event
    async def regenerate_qr(self) -> None:
        """Regenerate viewer code + QR (invalidates previous code)."""
        async for event in self.generate_qr():
            yield event
