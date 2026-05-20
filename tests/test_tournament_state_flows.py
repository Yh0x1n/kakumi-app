"""
KAKUMI Tests - Tournament State Flows
======================================
Tests para: TournamentEventLog model, Tournament.is_transitioning field,
            TournamentService (can_transition, validate_preconditions, transition_to),
            TournamentState event handlers con RBAC.

Sigue strict-TDD: RED → GREEN → TRIANGULATE → REFACTOR.
"""

import datetime

import pytest
import reflex as rx
from sqlmodel import select

from kakumi_app.models.tournament_model import Tournament, TournamentStatus


# =============================================================================
# PHASE 1.1 — TournamentEventLog model & Tournament.is_transitioning field
# =============================================================================


class TestTournamentEventLogModel:
    """Tests del modelo TournamentEventLog (audit log de transiciones)."""

    def test_create_event_log_minimal(self, sample_tournament):
        """Se puede crear un log con campos mínimos obligatorios."""
        from kakumi_app.models.tournament_event_log import TournamentEventLog

        with rx.session() as session:
            log = TournamentEventLog(
                tournament_id=sample_tournament.id,
                event_type="STATUS_CHANGE",
                old_status=TournamentStatus.PLANIFICADO.value,
                new_status=TournamentStatus.INSCRIPCION.value,
            )
            session.add(log)
            session.commit()
            session.refresh(log)

            assert log.id is not None
            assert log.tournament_id == sample_tournament.id
            assert log.event_type == "STATUS_CHANGE"
            assert log.old_status == TournamentStatus.PLANIFICADO.value
            assert log.new_status == TournamentStatus.INSCRIPCION.value

    def test_event_log_has_created_at_auto(self, sample_tournament):
        """created_at se asigna automáticamente al crear el log."""
        from kakumi_app.models.tournament_event_log import TournamentEventLog

        with rx.session() as session:
            log = TournamentEventLog(
                tournament_id=sample_tournament.id,
                event_type="STATUS_CHANGE",
            )
            session.add(log)
            session.commit()
            session.refresh(log)

            assert log.created_at is not None
            assert isinstance(log.created_at, datetime.datetime)

    def test_event_log_optional_fields_default_none(self, sample_tournament):
        """user_id y details son opcionales y defaultean a None."""
        from kakumi_app.models.tournament_event_log import TournamentEventLog

        with rx.session() as session:
            log = TournamentEventLog(
                tournament_id=sample_tournament.id,
                event_type="STATUS_CHANGE",
            )
            session.add(log)
            session.commit()
            session.refresh(log)

            assert log.user_id is None
            assert log.details is None

    def test_event_log_with_user_id_and_details(self, sample_tournament, sample_user):
        """Se puede guardar un log con user_id y details."""
        from kakumi_app.models.tournament_event_log import TournamentEventLog

        with rx.session() as session:
            log = TournamentEventLog(
                tournament_id=sample_tournament.id,
                event_type="STATUS_CHANGE",
                old_status=TournamentStatus.EN_CURSO.value,
                new_status=TournamentStatus.FINALIZADO.value,
                user_id=sample_user.id,
                details="Transición ejecutada por admin",
            )
            session.add(log)
            session.commit()
            session.refresh(log)

            assert log.user_id == sample_user.id
            assert log.details == "Transición ejecutada por admin"

    def test_event_log_table_name(self):
        """El modelo tiene el __tablename__ correcto."""
        from kakumi_app.models.tournament_event_log import TournamentEventLog

        assert TournamentEventLog.__tablename__ == "tournament_event_logs"

    def test_multiple_logs_for_same_tournament(self, sample_tournament):
        """Se pueden crear múltiples logs para el mismo torneo."""
        from kakumi_app.models.tournament_event_log import TournamentEventLog

        with rx.session() as session:
            log1 = TournamentEventLog(
                tournament_id=sample_tournament.id,
                event_type="STATUS_CHANGE",
                old_status=TournamentStatus.PLANIFICADO.value,
                new_status=TournamentStatus.INSCRIPCION.value,
            )
            log2 = TournamentEventLog(
                tournament_id=sample_tournament.id,
                event_type="STATUS_CHANGE",
                old_status=TournamentStatus.INSCRIPCION.value,
                new_status=TournamentStatus.VERIFICACION.value,
            )
            session.add(log1)
            session.add(log2)
            session.commit()

            # Verificar que ambos logs existen en la tabla
            logs = session.exec(
                select(TournamentEventLog).where(
                    TournamentEventLog.tournament_id == sample_tournament.id
                )
            ).all()
            assert len(logs) == 2


class TestTournamentIsTransitioning:
    """Tests del campo is_transitioning en el modelo Tournament."""

    def test_is_transitioning_default_false(self, sample_tournament):
        """is_transitioning defaultea a False en nuevos torneos."""
        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            assert tournament.is_transitioning is False

    def test_is_transitioning_can_be_set_true(self, sample_tournament):
        """is_transitioning puede setearse a True durante una transición."""
        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            tournament.is_transitioning = True
            session.add(tournament)
            session.commit()
            session.refresh(tournament)

            assert tournament.is_transitioning is True

    def test_is_transitioning_persists_across_sessions(self, sample_tournament):
        """El valor de is_transitioning persiste en la DB."""
        # Set to True en una session
        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            tournament.is_transitioning = True
            session.add(tournament)
            session.commit()

        # Verificar en otra session
        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            assert tournament.is_transitioning is True


# =============================================================================
# PHASE 2.1 — TournamentService: VALID_TRANSITIONS, can_transition()
# =============================================================================


class TestValidTransitions:
    """Tests de la tabla VALID_TRANSITIONS y can_transition()."""

    def test_can_transition_planificado_to_inscripcion(self):
        """PLANIFICADO → INSCRIPCION es una transición válida."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.can_transition(
            TournamentStatus.PLANIFICADO, TournamentStatus.INSCRIPCION
        )
        assert result is True

    def test_can_transition_planificado_to_archivado(self):
        """PLANIFICADO → ARCHIVADO (cancelar) es válida."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.can_transition(
            TournamentStatus.PLANIFICADO, TournamentStatus.ARCHIVADO
        )
        assert result is True

    def test_can_transition_inscripcion_to_verificacion(self):
        """INSCRIPCION → VERIFICACION es válida."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.can_transition(
            TournamentStatus.INSCRIPCION, TournamentStatus.VERIFICACION
        )
        assert result is True

    def test_can_transition_inscripcion_to_planificado(self):
        """INSCRIPCION → PLANIFICADO (reabrir) es válida."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.can_transition(
            TournamentStatus.INSCRIPCION, TournamentStatus.PLANIFICADO
        )
        assert result is True

    def test_can_transition_verificacion_to_en_curso(self):
        """VERIFICACION → EN_CURSO es válida."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.can_transition(
            TournamentStatus.VERIFICACION, TournamentStatus.EN_CURSO
        )
        assert result is True

    def test_can_transition_en_curso_to_finalizado(self):
        """EN_CURSO → FINALIZADO es válida."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.can_transition(
            TournamentStatus.EN_CURSO, TournamentStatus.FINALIZADO
        )
        assert result is True

    def test_can_transition_finalizado_to_archivado(self):
        """FINALIZADO → ARCHIVADO es válida."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.can_transition(
            TournamentStatus.FINALIZADO, TournamentStatus.ARCHIVADO
        )
        assert result is True

    def test_cannot_transition_en_curso_to_inscripcion(self):
        """EN_CURSO → INSCRIPCION es INVÁLIDA — debe finalizar primero."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.can_transition(
            TournamentStatus.EN_CURSO, TournamentStatus.INSCRIPCION
        )
        assert result is False

    def test_cannot_transition_finalizado_to_en_curso(self):
        """FINALIZADO → EN_CURSO es INVÁLIDA — no se puede reopen."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.can_transition(
            TournamentStatus.FINALIZADO, TournamentStatus.EN_CURSO
        )
        assert result is False

    def test_cannot_transition_from_archivado(self):
        """ARCHIVADO → cualquier estado es INVÁLIDA (estado terminal)."""
        from kakumi_app.services.tournament_service import TournamentService

        for target in TournamentStatus:
            result = TournamentService.can_transition(
                TournamentStatus.ARCHIVADO, target
            )
            assert result is False, f"ARCHIVADO → {target} debería ser inválido"

    def test_cannot_transition_verificacion_to_planificado(self):
        """VERIFICACION → PLANIFICADO es INVÁLIDA."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.can_transition(
            TournamentStatus.VERIFICACION, TournamentStatus.PLANIFICADO
        )
        assert result is False

    def test_cannot_transition_finalizado_to_planificado(self):
        """FINALIZADO → PLANIFICADO es INVÁLIDA."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.can_transition(
            TournamentStatus.FINALIZADO, TournamentStatus.PLANIFICADO
        )
        assert result is False


# =============================================================================
# PHASE 2.1 — TransitionResult dataclass
# =============================================================================


class TestTransitionResult:
    """Tests de TransitionResult — clase de resultado expresivo."""

    def test_transition_result_success_has_correct_fields(self):
        """Un TransitionResult exitoso tiene todos los campos requeridos."""
        from kakumi_app.services.tournament_service import TransitionResult

        result = TransitionResult(
            success=True,
            tournament_id=1,
            old_status=TournamentStatus.PLANIFICADO,
            new_status=TournamentStatus.INSCRIPCION,
        )

        assert result.success is True
        assert result.tournament_id == 1
        assert result.old_status == TournamentStatus.PLANIFICADO
        assert result.new_status == TournamentStatus.INSCRIPCION
        assert result.error_code is None
        assert result.error_message is None

    def test_transition_result_failure_has_error_fields(self):
        """Un TransitionResult fallido tiene error_code y error_message."""
        from kakumi_app.services.tournament_service import TransitionResult

        result = TransitionResult(
            success=False,
            tournament_id=42,
            old_status=TournamentStatus.EN_CURSO,
            new_status=None,
            error_code="INVALID_TRANSITION",
            error_message="No se puede ir de EN_CURSO a INSCRIPCION",
        )

        assert result.success is False
        assert result.error_code == "INVALID_TRANSITION"
        assert result.error_message is not None
        assert len(result.error_message) > 0

    def test_transition_result_has_timestamp(self):
        """TransitionResult incluye timestamp de cuando ocurrió."""
        from kakumi_app.services.tournament_service import TransitionResult

        result = TransitionResult(
            success=True,
            tournament_id=1,
            old_status=TournamentStatus.PLANIFICADO,
            new_status=TournamentStatus.INSCRIPCION,
        )

        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime.datetime)


# =============================================================================
# PHASE 2.1 — validate_preconditions() stub
# =============================================================================


class TestValidatePreconditionsStub:
    """Tests básicos del stub validate_preconditions().

    Verifica la firma y estructura del resultado sin probar lógica real
    (la lógica completa se prueba en Phase 2.2).
    """

    def test_validate_preconditions_returns_validation_result(self, sample_tournament):
        """validate_preconditions() retorna un ValidationResult (no None)."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.validate_preconditions(
            tournament_id=sample_tournament.id,
            to_status=TournamentStatus.VERIFICACION,
        )

        assert result is not None

    def test_validate_preconditions_result_has_can_proceed_attr(
        self, sample_tournament
    ):
        """ValidationResult tiene atributo can_proceed (bool)."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.validate_preconditions(
            tournament_id=sample_tournament.id,
            to_status=TournamentStatus.VERIFICACION,
        )

        assert hasattr(result, "can_proceed")
        assert isinstance(result.can_proceed, bool)

    def test_validate_preconditions_result_has_errors_list(self, sample_tournament):
        """ValidationResult tiene lista de errors."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.validate_preconditions(
            tournament_id=sample_tournament.id,
            to_status=TournamentStatus.VERIFICACION,
        )

        assert hasattr(result, "errors")
        assert isinstance(result.errors, list)


# =============================================================================
# PHASE 2.1 — ValidationResult y ValidationError dataclasses
# =============================================================================


class TestValidationResultClasses:
    """Tests de ValidationResult y ValidationError como estructuras de datos."""

    def test_validation_result_success_structure(self):
        """Un ValidationResult exitoso tiene can_proceed=True y errors vacíos."""
        from kakumi_app.services.tournament_service import ValidationResult

        result = ValidationResult(
            valid=True,
            transition="PLANIFICADO → INSCRIPCION",
            errors=[],
            warnings=[],
            can_proceed=True,
        )

        assert result.valid is True
        assert result.can_proceed is True
        assert len(result.errors) == 0

    def test_validation_error_structure(self):
        """ValidationError tiene code, message y campos opcionales."""
        from kakumi_app.services.exceptions import ValidationError

        error = ValidationError(
            code="NO_CATEGORIES",
            message="Debe crear al menos 1 categoría antes de verificar",
        )

        assert error.code == "NO_CATEGORIES"
        assert error.message == "Debe crear al menos 1 categoría antes de verificar"
        assert error.category_name is None

    def test_validation_error_with_category_name(self):
        """ValidationError puede incluir nombre de categoría específica."""
        from kakumi_app.services.exceptions import ValidationError

        error = ValidationError(
            code="INSUFFICIENT_ATHLETES",
            message="Categoría tiene 2 atletas, mínimo requerido: 4",
            category_name="Kata Junior Masculino",
            current_value=2,
            required_value=4,
        )

        assert error.category_name == "Kata Junior Masculino"
        assert error.current_value == 2
        assert error.required_value == 4


# =============================================================================
# PHASE 2.1 — transition_to() en TournamentService
# =============================================================================


class TestTransitionTo:
    """Tests de transition_to() — lógica completa de transición."""

    def test_transition_to_valid_returns_success(self, sample_tournament, sample_user):
        """Una transición válida retorna TransitionResult.success=True."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.INSCRIPCION,
            user_id=sample_user.id,
        )

        assert result.success is True
        assert result.new_status == TournamentStatus.INSCRIPCION
        assert result.old_status == TournamentStatus.PLANIFICADO

    def test_transition_to_updates_db_status(self, sample_tournament, sample_user):
        """transition_to() actualiza el estado en la DB."""
        from kakumi_app.services.tournament_service import TournamentService

        TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.INSCRIPCION,
            user_id=sample_user.id,
        )

        # Verificar en DB directamente
        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            assert tournament.status == TournamentStatus.INSCRIPCION.value

    def test_transition_to_creates_audit_log(self, sample_tournament, sample_user):
        """transition_to() crea un TournamentEventLog de auditoría."""
        from kakumi_app.services.tournament_service import TournamentService
        from kakumi_app.models.tournament_event_log import TournamentEventLog

        TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.INSCRIPCION,
            user_id=sample_user.id,
        )

        with rx.session() as session:
            logs = session.exec(
                select(TournamentEventLog).where(
                    TournamentEventLog.tournament_id == sample_tournament.id
                )
            ).all()
            assert len(logs) >= 1
            assert logs[0].event_type == "STATUS_CHANGE"
            assert logs[0].new_status == TournamentStatus.INSCRIPCION.value

    def test_transition_to_invalid_returns_failure(
        self, sample_tournament, sample_user
    ):
        """Una transición inválida retorna TransitionResult.success=False."""
        from kakumi_app.services.tournament_service import TournamentService

        # sample_tournament empieza en PLANIFICADO
        # intentar ir directo a EN_CURSO (inválido)
        result = TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.EN_CURSO,
            user_id=sample_user.id,
        )

        assert result.success is False
        assert result.error_code == "INVALID_TRANSITION"

    def test_transition_to_invalid_does_not_update_db(
        self, sample_tournament, sample_user
    ):
        """Una transición inválida NO modifica el estado en DB."""
        from kakumi_app.services.tournament_service import TournamentService

        TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.EN_CURSO,  # inválido desde PLANIFICADO
            user_id=sample_user.id,
        )

        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            assert tournament.status == TournamentStatus.PLANIFICADO.value

    def test_transition_to_nonexistent_tournament_returns_failure(self, sample_user):
        """Transición para tournament_id inexistente retorna fallo con error."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.transition_to(
            tournament_id=99999,
            new_status=TournamentStatus.INSCRIPCION,
            user_id=sample_user.id,
        )

        assert result.success is False
        assert result.error_code is not None

    def test_transition_to_archivado_from_terminal_state_returns_failure(
        self, sample_tournament, sample_user
    ):
        """Transición desde ARCHIVADO (terminal) falla con TERMINAL_STATE."""
        from kakumi_app.services.tournament_service import TournamentService

        # Primero llevar el torneo a ARCHIVADO
        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            tournament.status = TournamentStatus.ARCHIVADO.value
            session.add(tournament)
            session.commit()

        result = TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.PLANIFICADO,
            user_id=sample_user.id,
        )

        assert result.success is False
        assert result.error_code == "TERMINAL_STATE"

    def test_transition_to_while_in_progress_returns_failure(
        self, sample_tournament, sample_user
    ):
        """Si is_transitioning=True, retorna error TRANSITION_IN_PROGRESS."""
        from kakumi_app.services.tournament_service import TournamentService

        # Simular transición en progreso
        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            tournament.is_transitioning = True
            session.add(tournament)
            session.commit()

        result = TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.INSCRIPCION,
            user_id=sample_user.id,
        )

        assert result.success is False
        assert result.error_code == "TRANSITION_IN_PROGRESS"


# =============================================================================
# PHASE 2.2 — validate_preconditions() lógica real
# =============================================================================


class TestValidatePreconditionsLogic:
    """Tests de la lógica real de validate_preconditions()."""

    def test_no_categories_blocks_inscripcion_to_verificacion(self, sample_tournament):
        """Sin categorías, INSCRIPCION → VERIFICACION debe fallar con NO_CATEGORIES."""
        from kakumi_app.services.tournament_service import TournamentService

        # sample_tournament no tiene categorías
        result = TournamentService.validate_preconditions(
            tournament_id=sample_tournament.id,
            to_status=TournamentStatus.VERIFICACION,
        )

        assert result.can_proceed is False
        error_codes = [e.code for e in result.errors]
        assert "NO_CATEGORIES" in error_codes

    def test_with_categories_allows_inscripcion_to_verificacion(
        self, sample_tournament, sample_category
    ):
        """Con categoría existente, INSCRIPCION → VERIFICACION debe pasar."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.validate_preconditions(
            tournament_id=sample_tournament.id,
            to_status=TournamentStatus.VERIFICACION,
        )

        assert result.can_proceed is True
        error_codes = [e.code for e in result.errors]
        assert "NO_CATEGORIES" not in error_codes

    def test_no_arbiters_blocks_verificacion_to_en_curso(
        self, sample_tournament, sample_category
    ):
        """Sin árbitros, VERIFICACION → EN_CURSO falla con NO_ARBITERS."""
        from kakumi_app.services.tournament_service import TournamentService

        # Asegurar que hay una categoría pero sin árbitros
        result = TournamentService.validate_preconditions(
            tournament_id=sample_tournament.id,
            to_status=TournamentStatus.EN_CURSO,
        )

        assert result.can_proceed is False
        error_codes = [e.code for e in result.errors]
        assert "NO_ARBITERS" in error_codes

    def test_transitions_without_required_preconditions_pass_for_simple_states(
        self, sample_tournament
    ):
        """Transiciones sin precondiciones requeridas pasan."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.validate_preconditions(
            tournament_id=sample_tournament.id,
            to_status=TournamentStatus.INSCRIPCION,
        )

        assert result.can_proceed is True
        assert len(result.errors) == 0

    def test_archivado_transition_has_no_preconditions(self, sample_tournament):
        """Cancelar torneo (→ARCHIVADO) no requiere precondiciones."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.validate_preconditions(
            tournament_id=sample_tournament.id,
            to_status=TournamentStatus.ARCHIVADO,
        )

        assert result.can_proceed is True


# =============================================================================
# PHASE 2.3 — TournamentState RBAC integration
# =============================================================================


class TestTournamentStateRBAC:
    """Tests de integración RBAC en TournamentState."""

    def test_check_manage_tournament_permission_admin_allowed(self):
        """Un usuario ADMIN tiene permiso MANAGE_TOURNAMENT_STATUS."""
        from kakumi_app.services.auth_service import AuthService

        # Verificar que ADMIN puede hacer gestión de torneos
        allowed = AuthService.check_permission("ADMIN", "OPERATOR")
        assert allowed is True

    def test_check_manage_tournament_permission_viewer_denied(self):
        """Un usuario VIEWER NO tiene permiso para gestionar estados."""
        from kakumi_app.services.auth_service import AuthService

        # VIEWER no puede hacer lo que requiere OPERATOR o ADMIN
        allowed = AuthService.check_permission("VIEWER", "OPERATOR")
        assert allowed is False

    def test_tournament_state_has_required_state_vars(self):
        """TournamentState tiene las variables de estado requeridas."""
        from kakumi_app.states.tournament_state import TournamentState

        # Verificar que TournamentState tiene los atributos del diseño
        assert hasattr(TournamentState, "transition_error")
        assert hasattr(TournamentState, "is_transitioning")

    def test_tournament_state_has_semantic_event_handlers(self):
        """TournamentState expone los event handlers semánticos del diseño."""
        from kakumi_app.states.tournament_state import TournamentState

        assert callable(getattr(TournamentState, "open_registrations", None))
        assert callable(getattr(TournamentState, "close_registrations", None))
        assert callable(getattr(TournamentState, "start_competition", None))
        assert callable(getattr(TournamentState, "finish_competition", None))
        assert callable(getattr(TournamentState, "archive_tournament", None))
        assert callable(getattr(TournamentState, "reopen_registrations", None))


class TestTournamentWorkspaceState:
    """Tests de scaffolding del workspace /tournament."""

    @pytest.mark.anyio
    async def test_load_workspace_loads_tournaments_and_selects_first(
        self,
        sample_tournament,
    ):
        """Workspace carga torneos serializables y selecciona uno por defecto."""
        from kakumi_app.states.tournament_state import TournamentState

        state = TournamentState()

        await TournamentState.load_workspace.fn(state)

        assert state.tournaments
        assert isinstance(state.tournaments[0], dict)
        assert state.tournaments[0]["id"] == sample_tournament.id
        assert state.current_tournament is not None
        assert state.current_tournament["id"] == sample_tournament.id

    @pytest.mark.anyio
    async def test_load_workspace_with_no_tournaments_keeps_empty_selection(self):
        """Workspace vacío no debe inventar torneo actual."""
        from kakumi_app.states.tournament_state import TournamentState

        state = TournamentState()

        await TournamentState.load_workspace.fn(state)

        assert state.tournaments == []
        assert state.current_tournament is None

    @pytest.mark.anyio
    async def test_load_workspace_clears_previous_transition_feedback(
        self,
        sample_tournament,
    ):
        """Workspace refresh limpia errores/warnings viejos al seleccionar torneo."""
        from kakumi_app.states.tournament_state import TournamentState

        state = TournamentState()
        state.transition_error = "viejo"
        state.validation_warnings = ["warning viejo"]

        await TournamentState.load_workspace.fn(state)

        assert state.current_tournament is not None
        assert state.current_tournament["id"] == sample_tournament.id
        assert state.transition_error == ""
        assert state.validation_warnings == []

    @pytest.mark.anyio
    async def test_set_current_tournament_syncs_tatami_workspace_context(
        self,
        sample_tournament,
        monkeypatch,
    ):
        """Seleccionar torneo debe sincronizar tatamis y summary desde filas Tatami."""
        from kakumi_app.models.tournament_model import Tatami, Tournament
        from kakumi_app.states.tournament_category_state import TournamentCategoryState
        from kakumi_app.states.tournament_state import TournamentState
        from kakumi_app.states.tournament_tatami_state import TournamentTatamiState

        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            assert tournament is not None
            tournament.tatami_count = 9
            session.add(tournament)
            session.add(Tatami(name="Tatami 1", tournament_id=sample_tournament.id))
            session.add(
                Tatami(
                    name="Tatami 2",
                    tournament_id=sample_tournament.id,
                    is_active=False,
                )
            )
            session.commit()

        state = TournamentState()
        category_state = TournamentCategoryState()
        tatami_state = TournamentTatamiState()

        async def fake_get_state(self, state_cls):
            if state_cls is TournamentCategoryState:
                return category_state
            assert state_cls is TournamentTatamiState
            return tatami_state

        monkeypatch.setattr(TournamentState, "get_state", fake_get_state)

        await TournamentState.set_current_tournament.fn(state, sample_tournament.id)

        assert state.current_tournament is not None
        assert state.current_tournament["tatami_count"] == 2
        assert tatami_state.current_tournament_id == sample_tournament.id
        assert tatami_state.declared_tatami_count == 2
        assert tatami_state.active_tatami_count == 1

    @pytest.mark.anyio
    async def test_set_current_tournament_preserves_sync_failure_message(
        self,
        sample_tournament,
        monkeypatch,
    ):
        """Sync failures must remain visible after selection completes."""
        from kakumi_app.states import tournament_state as state_module
        from kakumi_app.states.tournament_category_state import TournamentCategoryState
        from kakumi_app.states.tournament_state import TournamentState
        from kakumi_app.states.tournament_tatami_state import TournamentTatamiState

        state = TournamentState()
        tatami_state = TournamentTatamiState()
        toasts: list[str] = []

        async def fake_get_state(self, state_cls):
            if state_cls is TournamentCategoryState:
                raise RuntimeError("sync categoría rota")
            assert state_cls is TournamentTatamiState
            return tatami_state

        monkeypatch.setattr(TournamentState, "get_state", fake_get_state)
        monkeypatch.setattr(
            state_module.rx.toast,
            "error",
            lambda message: toasts.append(message) or message,
        )

        await TournamentState.set_current_tournament.fn(state, sample_tournament.id)

        assert state.current_tournament is not None
        assert state.current_tournament["id"] == sample_tournament.id
        assert state.transition_error == (
            "No se pudo sincronizar categorías del torneo: sync categoría rota"
        )
        assert toasts == [
            "No se pudo sincronizar categorías del torneo: sync categoría rota"
        ]

    @pytest.mark.anyio
    async def test_sync_auth_context_copies_operator_role_from_auth_state(
        self, monkeypatch
    ):
        """Workspace debe leer auth actual y reflejar permisos de operador."""
        from kakumi_app.states.auth_state import AuthState
        from kakumi_app.states.tournament_state import TournamentState

        state = TournamentState()
        auth_state = AuthState()
        auth_state.is_authenticated = True
        auth_state.user_role = "OPERATOR"
        auth_state.current_user = {"id": 77, "role": "OPERATOR"}

        # Prevent _load_user_from_token from resetting test-set values
        monkeypatch.setattr(AuthState, "_load_user_from_token", lambda self: None)

        async def fake_get_state(self, state_cls):
            assert state_cls is AuthState
            return auth_state

        monkeypatch.setattr(TournamentState, "get_state", fake_get_state)

        await TournamentState.sync_auth_context.fn(state)

        assert state._current_user_id == 77
        assert state._current_user_role == "OPERATOR"

    @pytest.mark.anyio
    async def test_sync_auth_context_clears_role_when_user_not_authenticated(
        self, monkeypatch
    ):
        """Sin sesión autenticada, lifecycle debe quedar oculto."""
        from kakumi_app.states.auth_state import AuthState
        from kakumi_app.states.tournament_state import TournamentState

        state = TournamentState()
        state._current_user_id = 55
        state._current_user_role = "ADMIN"
        auth_state = AuthState()
        auth_state.is_authenticated = False
        auth_state.user_role = ""
        auth_state.current_user = None

        async def fake_get_state(self, state_cls):
            assert state_cls is AuthState
            return auth_state

        monkeypatch.setattr(TournamentState, "get_state", fake_get_state)

        await TournamentState.sync_auth_context.fn(state)

        assert state._current_user_id == 0
        assert state._current_user_role == ""

    def test_show_lifecycle_controls_requires_operator_role(self):
        """Solo OPERATOR o ADMIN deben ver controles de ciclo."""
        from kakumi_app.states.tournament_state import TournamentState

        state = TournamentState()
        state._current_user_role = "VIEWER"
        assert state.show_lifecycle_controls is False

        state._current_user_role = "OPERATOR"
        assert state.show_lifecycle_controls is True

        state._current_user_role = "ADMIN"
        assert state.show_lifecycle_controls is True

    def test_show_lifecycle_actions_follow_transition_table(self):
        """Workspace debe exponer solo acciones válidas para estado actual."""
        from kakumi_app.states.tournament_state import TournamentState

        state = TournamentState()
        state._current_user_role = "OPERATOR"

        state.current_tournament = {"id": 1, "status": TournamentStatus.PLANIFICADO.value}
        assert state.show_open_registrations_action is True
        assert state.show_close_registrations_action is False
        assert state.show_start_competition_action is False
        assert state.show_finish_competition_action is False
        assert state.show_archive_tournament_action is True
        assert state.show_reopen_registrations_action is False
        assert state.show_cancel_tournament_action is False

        state.current_tournament = {"id": 1, "status": TournamentStatus.INSCRIPCION.value}
        assert state.show_open_registrations_action is False
        assert state.show_close_registrations_action is True
        assert state.show_reopen_registrations_action is True

        state.current_tournament = {"id": 1, "status": TournamentStatus.VERIFICACION.value}
        assert state.show_start_competition_action is True

        state.current_tournament = {"id": 1, "status": TournamentStatus.EN_CURSO.value}
        assert state.show_finish_competition_action is True

        state.current_tournament = {"id": 1, "status": TournamentStatus.FINALIZADO.value}
        assert state.show_archive_tournament_action is True

    def test_admin_only_cancel_action_hidden_for_operator(self):
        """Cancelar torneo queda visible solo para ADMIN."""
        from kakumi_app.states.tournament_state import TournamentState

        state = TournamentState()
        state.current_tournament = {"id": 1, "status": TournamentStatus.PLANIFICADO.value}

        state._current_user_role = "OPERATOR"
        assert state.show_cancel_tournament_action is False

        state._current_user_role = "ADMIN"
        assert state.show_cancel_tournament_action is True

    @pytest.mark.anyio
    async def test_open_registrations_surfaces_service_success_and_warnings(
        self,
        sample_tournament,
        monkeypatch,
    ):
        """UI/state debe delegar a service owner y propagar warnings."""
        from kakumi_app.services.tournament_service import TransitionResult, Warning
        from kakumi_app.states.tournament_state import TournamentState

        state = TournamentState()
        state._current_user_id = 9
        state._current_user_role = "OPERATOR"
        state.current_tournament = sample_tournament.model_dump(mode="json")

        calls: list[tuple[int, TournamentStatus, int]] = []

        def fake_transition_to(tournament_id, new_status, user_id, dry_run=False):
            calls.append((tournament_id, new_status, user_id))
            assert dry_run is False
            return TransitionResult(
                success=True,
                tournament_id=tournament_id,
                old_status=TournamentStatus.PLANIFICADO,
                new_status=TournamentStatus.INSCRIPCION,
                warnings=[Warning(code="REMINDER", message="Configurar horario")],
            )

        monkeypatch.setattr(
            "kakumi_app.states.tournament_state.TournamentService.transition_to",
            fake_transition_to,
        )
        monkeypatch.setattr(
            "kakumi_app.states.tournament_state.rx.toast.warning",
            lambda message, duration=5000: (message, duration),
        )

        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            tournament.status = TournamentStatus.INSCRIPCION.value
            session.add(tournament)
            session.commit()

        events = [
            event async for event in TournamentState.open_registrations.fn(state)
        ]

        assert calls == [
            (sample_tournament.id, TournamentStatus.INSCRIPCION, 9)
        ]
        assert state.validation_warnings == ["Configurar horario"]
        assert state.transition_error == ""
        assert state.current_tournament is not None
        assert state.current_tournament["status"] == TournamentStatus.INSCRIPCION.value
        assert events == [("Configurar horario", 5000)]

    @pytest.mark.anyio
    async def test_close_registrations_blocks_viewer_before_service_call(
        self,
        sample_tournament,
        monkeypatch,
    ):
        """Viewer no puede ejecutar transición ni tocar service."""
        from kakumi_app.states.tournament_state import TournamentState

        state = TournamentState()
        state._current_user_id = 4
        state._current_user_role = "VIEWER"
        state.current_tournament = sample_tournament.model_dump(mode="json")

        called = False

        def fake_transition_to(*args, **kwargs):
            nonlocal called
            called = True
            raise AssertionError("service no debe invocarse")

        monkeypatch.setattr(
            "kakumi_app.states.tournament_state.TournamentService.transition_to",
            fake_transition_to,
        )

        events = [
            event async for event in TournamentState.close_registrations.fn(state)
        ]

        assert called is False
        assert events == []
        assert "No tiene permisos" in state.transition_error

    @pytest.mark.anyio
    async def test_cancel_tournament_requires_admin_and_skips_service_for_operator(
        self,
        sample_tournament,
        monkeypatch,
    ):
        """Cancelar desde workspace debe respetar guard admin-only."""
        from kakumi_app.states.tournament_state import TournamentState

        state = TournamentState()
        state._current_user_id = 4
        state._current_user_role = "OPERATOR"
        state.current_tournament = sample_tournament.model_dump(mode="json")

        called = False

        def fake_transition_to(*args, **kwargs):
            nonlocal called
            called = True
            raise AssertionError("service no debe invocarse")

        monkeypatch.setattr(
            "kakumi_app.states.tournament_state.TournamentService.transition_to",
            fake_transition_to,
        )
        monkeypatch.setattr(
            "kakumi_app.states.tournament_state.rx.toast.error",
            lambda message, duration=5000: (message, duration),
        )

        events = [event async for event in TournamentState.cancel_tournament.fn(state)]

        assert called is False
        assert "Solo administradores" in state.transition_error
        assert events == [
            (
                "Solo administradores pueden cancelar un torneo en estado PLANIFICADO.",
                5000,
            )
        ]


# =============================================================================
# SPEC: tournament-state-validation — Escenarios adicionales (CRITICAL 2)
# =============================================================================


class TestValidationPassesReadyToStart:
    """Scenario: Validation Passes - Ready to Start.

    VERIFICACION → EN_CURSO exitoso cuando hay árbitros y atletas suficientes.
    """

    def test_validation_passes_with_arbiters_and_athletes(
        self, sample_tournament, sample_category
    ):
        """Con árbitros y atletas suficientes, EN_CURSO debe pasar."""
        from kakumi_app.services.tournament_service import TournamentService
        from kakumi_app.models.athlete_model import Athlete
        from kakumi_app.models.referee_model import Referee

        # Crear 3 árbitros disponibles
        with rx.session() as session:
            for i in range(3):
                ref = Referee(
                    name=f"Árbitro {i}",
                    license_number=f"REF-TEST-{i}",
                    license_level="NATIONAL",
                    role="REFEREE",
                    is_available=True,
                    dojo="Fed Test",
                    email=f"ref{i}@test.test",
                )
                session.add(ref)

            # Crear 4 atletas en la categoría (mínimo WKF)
            for i in range(4):
                athlete = Athlete(
                    name=f"Atleta {i}",
                    age=26,
                    gender="MALE",
                    email=f"atleta{i}@test.test",
                    weight_kg=70.0,
                    belt_rank="Negro",
                    dojo="Dojo Test",
                    nationality="ARG",
                    license_number=f"ATL-{i}",
                    is_active=True,
                )
                session.add(athlete)
            session.commit()

        result = TournamentService.validate_preconditions(
            tournament_id=sample_tournament.id,
            to_status=TournamentStatus.EN_CURSO,
        )

        assert result.can_proceed is True
        error_codes = [e.code for e in result.errors]
        assert "NO_ARBITERS" not in error_codes
        assert "INSUFFICIENT_ATHLETES" not in error_codes


class TestValidationPassesReadyToFinish:
    """Scenario: Validation Passes - Ready to Finish.

    EN_CURSO → FINALIZADO exitoso cuando todos los matches están completados.
    """

    def test_validation_passes_when_all_matches_completed(
        self, sample_tournament, sample_match
    ):
        """Con todos los matches en COMPLETED, EN_CURSO → FINALIZADO debe pasar."""
        from kakumi_app.services.tournament_service import TournamentService

        # Marcar el match como completado
        with rx.session() as session:
            from kakumi_app.models.tournament_model import Match, MatchStatus

            match = session.get(Match, sample_match.id)
            match.status = MatchStatus.COMPLETED.value
            session.add(match)
            session.commit()

        result = TournamentService.validate_preconditions(
            tournament_id=sample_tournament.id,
            to_status=TournamentStatus.FINALIZADO,
        )

        assert result.can_proceed is True
        error_codes = [e.code for e in result.errors]
        assert "MATCHES_INCOMPLETE" not in error_codes

    def test_transition_to_finalizado_succeeds_when_all_matches_completed(
        self, sample_tournament, sample_match, sample_user
    ):
        """transition_to FINALIZADO ok si todos matches completados."""
        from kakumi_app.services.tournament_service import TournamentService

        # Llevar el torneo a EN_CURSO
        with rx.session() as session:
            from kakumi_app.models.tournament_model import Match, MatchStatus

            tournament = session.get(Tournament, sample_tournament.id)
            tournament.status = TournamentStatus.EN_CURSO.value
            session.add(tournament)
            # Marcar match como completado
            match = session.get(Match, sample_match.id)
            match.status = MatchStatus.COMPLETED.value
            session.add(match)
            session.commit()

        result = TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.FINALIZADO,
            user_id=sample_user.id,
        )

        assert result.success is True
        assert result.new_status == TournamentStatus.FINALIZADO


class TestInsufficientAthletesOneCategory:
    """Scenario: Insufficient Athletes in One Category."""

    def test_one_category_with_insufficient_athletes_blocks_transition(
        self, sample_tournament, sample_category
    ):
        """Una categoría con 2 atletas (< 4) bloquea VERIFICACION → EN_CURSO."""
        from kakumi_app.services.tournament_service import TournamentService
        from kakumi_app.models.athlete_model import Athlete
        from kakumi_app.models.referee_model import Referee

        # Crear 3 árbitros para no bloquear por NO_ARBITERS
        with rx.session() as session:
            for i in range(3):
                ref = Referee(
                    name=f"Árbitro {i}",
                    license_number=f"REF-INS-{i}",
                    license_level="NATIONAL",
                    role="REFEREE",
                    is_available=True,
                    dojo="Fed Test",
                    email=f"refins{i}@test.test",
                )
                session.add(ref)

            # Crear solo 1 atleta en la categoría (insuficiente, mínimo 2)
            athlete = Athlete(
                name="Atleta Kata 0",
                age=26,
                gender="MALE",
                email="kata0@test.test",
                weight_kg=70.0,
                belt_rank="Negro",
                dojo="Dojo Test",
                nationality="ARG",
                license_number="KATA-0",
                is_active=True,
            )
            session.add(athlete)
            session.commit()

        result = TournamentService.validate_preconditions(
            tournament_id=sample_tournament.id,
            to_status=TournamentStatus.EN_CURSO,
        )

        assert result.can_proceed is False
        error_codes = [e.code for e in result.errors]
        assert "INSUFFICIENT_ATHLETES" in error_codes

        # Verificar que el error incluye el nombre de la categoría
        insufficient_errors = [
            e for e in result.errors if e.code == "INSUFFICIENT_ATHLETES"
        ]
        assert len(insufficient_errors) >= 1
        assert insufficient_errors[0].category_name == sample_category.name
        assert insufficient_errors[0].current_value == 1
        assert insufficient_errors[0].required_value == 2


class TestMultipleValidationFailures:
    """Scenario: Multiple Validation Failures."""

    def test_multiple_errors_returned_as_list(self, sample_tournament):
        """Sin categorías, retorna lista de errores (al menos NO_CATEGORIES)."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.validate_preconditions(
            tournament_id=sample_tournament.id,
            to_status=TournamentStatus.VERIFICACION,
        )

        assert isinstance(result.errors, list)
        assert len(result.errors) >= 1
        error_codes = [e.code for e in result.errors]
        assert "NO_CATEGORIES" in error_codes

    def test_en_curso_can_return_multiple_errors(
        self, sample_tournament, sample_category
    ):
        """EN_CURSO puede retornar errores múltiples."""
        from kakumi_app.services.tournament_service import TournamentService
        from kakumi_app.models.athlete_model import Athlete

        # Crear solo 1 atleta (insuficiente) — sin árbitros
        with rx.session() as session:
            athlete = Athlete(
                name="Atleta Solo",
                age=26,
                gender="MALE",
                email="solo@test.test",
                weight_kg=70.0,
                belt_rank="Negro",
                dojo="Dojo Test",
                nationality="ARG",
                license_number="ATL-SOLO",
                is_active=True,
            )
            session.add(athlete)
            session.commit()

        result = TournamentService.validate_preconditions(
            tournament_id=sample_tournament.id,
            to_status=TournamentStatus.EN_CURSO,
        )

        assert result.can_proceed is False
        assert len(result.errors) >= 2
        error_codes = [e.code for e in result.errors]
        assert "INSUFFICIENT_ATHLETES" in error_codes
        assert "NO_ARBITERS" in error_codes


class TestIncompleteMatchesPreventFinish:
    """Scenario: Incomplete Matches Prevent Finish."""

    def test_pending_match_blocks_en_curso_to_finalizado(
        self, sample_tournament, sample_match
    ):
        """Un match en estado PENDING bloquea EN_CURSO → FINALIZADO."""
        from kakumi_app.services.tournament_service import TournamentService

        # El sample_match ya está en PENDING por defecto
        result = TournamentService.validate_preconditions(
            tournament_id=sample_tournament.id,
            to_status=TournamentStatus.FINALIZADO,
        )

        assert result.can_proceed is False
        error_codes = [e.code for e in result.errors]
        assert "MATCHES_INCOMPLETE" in error_codes

        incomplete_errors = [e for e in result.errors if e.code == "MATCHES_INCOMPLETE"]
        assert incomplete_errors[0].current_value >= 1


class TestDryRunValidation:
    """Scenario: Dry Run Validation."""

    def test_dry_run_returns_validation_without_state_change(
        self, sample_tournament, sample_user
    ):
        """dry_run=True retorna resultado sin cambiar el estado del torneo."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.INSCRIPCION,
            user_id=sample_user.id,
            dry_run=True,
        )

        # Debe retornar éxito (las precondiciones se cumplen)
        assert result.success is True
        assert result.new_status == TournamentStatus.INSCRIPCION

        # El estado en DB NO debe haber cambiado
        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            assert tournament.status == TournamentStatus.PLANIFICADO.value

    def test_dry_run_with_failing_validation_returns_failure(
        self, sample_tournament, sample_user
    ):
        """dry_run=True con validaciones fallidas retorna fallo sin cambiar estado."""
        from kakumi_app.services.tournament_service import TournamentService

        # VERIFICACION → EN_CURSO sin árbitros ni atletas — debe fallar
        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            tournament.status = TournamentStatus.VERIFICACION.value
            session.add(tournament)
            session.commit()

        result = TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.EN_CURSO,
            user_id=sample_user.id,
            dry_run=True,
        )

        assert result.success is False
        # Estado en DB sigue siendo VERIFICACION
        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            assert tournament.status == TournamentStatus.VERIFICACION.value


class TestWarningOnlyValidation:
    """Scenario: Warning-Only Validation Failure.

    Las validaciones WARNING no bloquean la transición.
    La implementación actual chequea start_date pero el modelo Tournament
    tiene start_date como NOT NULL, por lo que el warning NO_SCHEDULE
    sólo aplica cuando el campo existe pero está vacío (lógica futura).
    Acá verificamos que los warnings en ValidationResult NO bloquean can_proceed.
    """

    def test_validation_result_with_warnings_allows_proceeding(self):
        """Un ValidationResult con warnings (sin errors) tiene can_proceed=True."""
        from kakumi_app.services.tournament_service import (
            ValidationResult,
            Warning as ServiceWarning,
        )

        result = ValidationResult(
            valid=True,
            transition="VERIFICACION → EN_CURSO",
            errors=[],
            warnings=[
                ServiceWarning(
                    code="NO_SCHEDULE",
                    message="El horario del torneo no está configurado",
                )
            ],
            can_proceed=True,
        )

        # can_proceed debe ser True aún con warnings
        assert result.can_proceed is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "NO_SCHEDULE"

    def test_warnings_do_not_block_transition_with_required_passing(
        self, sample_tournament, sample_category, sample_user
    ):
        """Con árbitros y atletas suficientes, VERIFICACION → EN_CURSO pasa.

        El fixture sample_tournament ya tiene start_date configurado, así que
        la validación required pasa y no hay warnings (start_date es NOT NULL
        en el modelo — el warning NO_SCHEDULE sólo aplica en casos futuros).
        """
        from kakumi_app.services.tournament_service import TournamentService
        from kakumi_app.models.athlete_model import Athlete
        from kakumi_app.models.referee_model import Referee

        # Crear árbitros y atletas suficientes
        with rx.session() as session:
            for i in range(3):
                ref = Referee(
                    name=f"Árbitro Warn2 {i}",
                    license_number=f"REF-WARN2-{i}",
                    license_level="NATIONAL",
                    role="REFEREE",
                    is_available=True,
                    dojo="Fed Test",
                    email=f"refwarn2{i}@test.test",
                )
                session.add(ref)

            for i in range(4):
                athlete = Athlete(
                    name=f"Atleta Warn2 {i}",
                    age=26,
                    gender="MALE",
                    email=f"warn2{i}@test.test",
                    weight_kg=70.0,
                    belt_rank="Negro",
                    dojo="Dojo Test",
                    nationality="ARG",
                    license_number=f"WARN2-{i}",
                    is_active=True,
                )
                session.add(athlete)
            session.commit()

        result = TournamentService.validate_preconditions(
            tournament_id=sample_tournament.id,
            to_status=TournamentStatus.EN_CURSO,
        )

        # can_proceed es True cuando todas las REQUIRED pasan
        assert result.can_proceed is True
        assert len(result.errors) == 0


class TestAllCategoriesInsufficientAthletes:
    """Scenario: All Categories Have Insufficient Athletes."""

    def test_multiple_categories_all_insufficient_returns_all_errors(
        self, sample_tournament
    ):
        """Con 2 categorías sin atletas, retorna INSUFFICIENT_ATHLETES por cada una."""
        from kakumi_app.services.tournament_service import TournamentService
        from kakumi_app.models.tournament_model import (
            TournamentCategory,
            CategoryGender,
            CategoryStatus,
            CompetitionSystem,
            Modality,
        )
        from kakumi_app.models.referee_model import Referee

        # Crear 3 árbitros para no bloquear por NO_ARBITERS
        with rx.session() as session:
            for i in range(3):
                ref = Referee(
                    name=f"Árbitro AllCat {i}",
                    license_number=f"REF-ALLCAT-{i}",
                    license_level="NATIONAL",
                    role="REFEREE",
                    is_available=True,
                    dojo="Fed Test",
                    email=f"refallcat{i}@test.test",
                )
                session.add(ref)

            # Crear 2 categorías sin atletas
            for i in range(2):
                cat = TournamentCategory(
                    name=f"Categoría Vacía {i}",
                    modality=Modality.KATA_INDIVIDUAL.value,
                    gender=CategoryGender.MALE.value,
                    min_age=18,
                    max_age=35,
                    competition_system=CompetitionSystem.ELIMINATION.value,
                    bracket_size=8,
                    status=CategoryStatus.PENDING.value,
                    tournament_id=sample_tournament.id,
                    judge_panel_size=5,
                )
                session.add(cat)
            session.commit()

        result = TournamentService.validate_preconditions(
            tournament_id=sample_tournament.id,
            to_status=TournamentStatus.EN_CURSO,
        )

        assert result.can_proceed is False
        insufficient_errors = [
            e for e in result.errors if e.code == "INSUFFICIENT_ATHLETES"
        ]
        # Debe haber 1 error por cada categoría con insuficientes atletas (2)
        assert len(insufficient_errors) == 2


# =============================================================================
# SPEC: tournament-state-transitions — Escenarios adicionales (CRITICAL 2)
# =============================================================================


class TestStartCompetitionTransition:
    """Scenario: Start Competition — VERIFICACION → EN_CURSO exitoso."""

    def test_start_competition_from_verificacion_succeeds(
        self, sample_tournament, sample_category, sample_user
    ):
        """transition_to EN_CURSO desde VERIFICACION con condiciones válidas."""
        from kakumi_app.services.tournament_service import TournamentService
        from kakumi_app.models.athlete_model import Athlete
        from kakumi_app.models.referee_model import Referee

        # Setup: llevar torneo a VERIFICACION y crear árbitros + atletas
        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            tournament.status = TournamentStatus.VERIFICACION.value
            session.add(tournament)

            for i in range(3):
                ref = Referee(
                    name=f"Árbitro Start {i}",
                    license_number=f"REF-START-{i}",
                    license_level="NATIONAL",
                    role="REFEREE",
                    is_available=True,
                    dojo="Fed Test",
                    email=f"refstart{i}@test.test",
                )
                session.add(ref)

            for i in range(4):
                athlete = Athlete(
                    name=f"Atleta Start {i}",
                    age=26,
                    gender="MALE",
                    email=f"start{i}@test.test",
                    weight_kg=70.0,
                    belt_rank="Negro",
                    dojo="Dojo Test",
                    nationality="ARG",
                    license_number=f"START-{i}",
                    is_active=True,
                )
                session.add(athlete)
            session.commit()

        result = TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.EN_CURSO,
            user_id=sample_user.id,
        )

        assert result.success is True
        assert result.new_status == TournamentStatus.EN_CURSO
        assert result.old_status == TournamentStatus.VERIFICACION


class TestCompleteTournamentTransition:
    """Scenario: Complete Tournament — EN_CURSO → FINALIZADO exitoso."""

    def test_complete_tournament_from_en_curso_succeeds(
        self, sample_tournament, sample_user
    ):
        """transition_to FINALIZADO desde EN_CURSO sin matches incompletos."""
        from kakumi_app.services.tournament_service import TournamentService

        # Sin matches: no hay matches incompletos → válido
        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            tournament.status = TournamentStatus.EN_CURSO.value
            session.add(tournament)
            session.commit()

        result = TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.FINALIZADO,
            user_id=sample_user.id,
        )

        assert result.success is True
        assert result.new_status == TournamentStatus.FINALIZADO
        assert result.old_status == TournamentStatus.EN_CURSO

    def test_complete_tournament_allows_informal_category_without_matches(
        self,
        sample_tournament,
        sample_user,
    ):
        """Informal Kata category finalized should not require match rows."""
        from kakumi_app.services.tournament_service import TournamentService
        from kakumi_app.models.athlete_model import Athlete
        from kakumi_app.models.tournament_model import (
            TournamentCategory,
            Modality,
            CategoryGender,
            CompetitionSystem,
            CategoryStatus,
        )

        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            tournament.status = TournamentStatus.EN_CURSO.value
            session.add(tournament)

            category = TournamentCategory(
                name="Informal Completion",
                modality=Modality.KATA_INDIVIDUAL.value,
                gender=CategoryGender.MIXED.value,
                min_age=16,
                max_age=40,
                competition_system=CompetitionSystem.ROUND_ROBIN.value,
                bracket_size=8,
                status=CategoryStatus.COMPLETED.value,
                tournament_id=sample_tournament.id,
                kata_flow_mode="INFORMAL",
                first_place_id=1,
                second_place_id=2,
                third_place_ids="[3]",
            )
            session.add(category)
            # Add matching athletes so bracket generation does not fail
            for i in range(2):
                athlete = Athlete(
                    name=f"Informal Athlete {i}",
                    age=20,
                    gender="MALE",
                    email=f"informal{i}@test.test",
                    belt_rank="Negro",
                    is_active=True,
                )
                session.add(athlete)
            session.commit()

        result = TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.FINALIZADO,
            user_id=sample_user.id,
        )

        assert result.success is True

    def test_complete_tournament_blocks_when_informal_category_not_completed(
        self,
        sample_tournament,
        sample_user,
    ):
        """Informal category in progress blocks EN_CURSO -> FINALIZADO."""
        from kakumi_app.services.tournament_service import TournamentService
        from kakumi_app.models.athlete_model import Athlete
        from kakumi_app.models.tournament_model import (
            TournamentCategory,
            Modality,
            CategoryGender,
            CompetitionSystem,
            CategoryStatus,
        )

        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            tournament.status = TournamentStatus.EN_CURSO.value
            session.add(tournament)

            category = TournamentCategory(
                name="Informal Pending",
                modality=Modality.KATA_INDIVIDUAL.value,
                gender=CategoryGender.MIXED.value,
                min_age=16,
                max_age=40,
                competition_system=CompetitionSystem.ROUND_ROBIN.value,
                bracket_size=8,
                status=CategoryStatus.IN_PROGRESS.value,
                tournament_id=sample_tournament.id,
                kata_flow_mode="INFORMAL",
            )
            session.add(category)
            # Add matching athletes so bracket generation does not fail
            for i in range(2):
                athlete = Athlete(
                    name=f"Pending Athlete {i}",
                    age=20,
                    gender="MALE",
                    email=f"pending{i}@test.test",
                    belt_rank="Negro",
                    is_active=True,
                )
                session.add(athlete)
            session.commit()

        result = TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.FINALIZADO,
            user_id=sample_user.id,
        )

        assert result.success is False


class TestReopenRegistrationsTransition:
    """Scenario: Reopen Registrations — INSCRIPCION → PLANIFICADO exitoso."""

    def test_reopen_registrations_from_inscripcion_succeeds(
        self, sample_tournament, sample_user
    ):
        """transition_to PLANIFICADO desde INSCRIPCION es válido."""
        from kakumi_app.services.tournament_service import TournamentService

        # Llevar el torneo a INSCRIPCION
        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            tournament.status = TournamentStatus.INSCRIPCION.value
            session.add(tournament)
            session.commit()

        result = TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.PLANIFICADO,
            user_id=sample_user.id,
        )

        assert result.success is True
        assert result.new_status == TournamentStatus.PLANIFICADO
        assert result.old_status == TournamentStatus.INSCRIPCION


class TestCancelTournamentTransition:
    """Scenario: Cancel Tournament — PLANIFICADO → ARCHIVADO exitoso."""

    def test_cancel_tournament_from_planificado_succeeds(
        self, sample_tournament, sample_user
    ):
        """transition_to ARCHIVADO desde PLANIFICADO es válido (cancelar)."""
        from kakumi_app.services.tournament_service import TournamentService

        result = TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.ARCHIVADO,
            user_id=sample_user.id,
        )

        assert result.success is True
        assert result.new_status == TournamentStatus.ARCHIVADO
        assert result.old_status == TournamentStatus.PLANIFICADO


class TestInvalidCurrentStateTransition:
    """Scenario: Invalid Current State — transición desde estado no válido."""

    def test_transition_from_invalid_state_string_returns_error(
        self, sample_tournament, sample_user
    ):
        """Si el estado en DB es un string inválido, retorna INVALID_CURRENT_STATE."""
        from kakumi_app.services.tournament_service import TournamentService

        # Setear un estado inválido directamente en DB
        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            tournament.status = "ESTADO_INVALIDO"
            session.add(tournament)
            session.commit()

        result = TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.INSCRIPCION,
            user_id=sample_user.id,
        )

        assert result.success is False
        assert result.error_code == "INVALID_CURRENT_STATE"


class TestInvalidTransitionAudited:
    """Scenario: Invalid Transition Attempts Audited.

    Spec req 13: SHOULD loguear intentos de transición inválida.
    """

    def test_invalid_transition_creates_audit_log(self, sample_tournament, sample_user):
        """Un intento de transición inválida debe generar un audit log."""
        from kakumi_app.services.tournament_service import TournamentService
        from kakumi_app.models.tournament_event_log import TournamentEventLog

        # Intentar transición inválida PLANIFICADO → EN_CURSO
        TournamentService.transition_to(
            tournament_id=sample_tournament.id,
            new_status=TournamentStatus.EN_CURSO,
            user_id=sample_user.id,
        )

        with rx.session() as session:
            logs = session.exec(
                select(TournamentEventLog).where(
                    TournamentEventLog.tournament_id == sample_tournament.id,
                    TournamentEventLog.event_type == "TRANSITION_ATTEMPT_FAILED",
                )
            ).all()

        # Debe haber al menos 1 log de intento fallido
        assert len(logs) >= 1
        assert logs[0].old_status == TournamentStatus.PLANIFICADO.value
