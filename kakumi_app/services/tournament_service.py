"""
KAKUMI - Tournament Service
=============================
Servicio central para la gestión de transiciones de estado de torneos.
Implementa las reglas de negocio WKF 2026 para flujos de estado.

Patrón: service-first, siguiendo AuthService como referencia.
"""

from dataclasses import dataclass, field
from typing import List, Optional

import reflex as rx
from sqlmodel import select

from kakumi_app.models.referee_model import Referee
from kakumi_app.models.tournament_event_log import TournamentEventLog
from kakumi_app.models.tournament_model import (
    CategoryStatus,
    CompetitionSystem,
    Match,
    MatchStatus,
    Tournament,
    TournamentCategory,
    TournamentStatus,
)
from kakumi_app.services.bracket_service import generate_bracket
from kakumi_app.services.exceptions import ValidationError

# =============================================================================
# VALID TRANSITIONS TABLE
# Reglas estáticas WKF 2026 — no requieren configuración en DB.
# =============================================================================

VALID_TRANSITIONS: dict[TournamentStatus, list[TournamentStatus]] = {
    TournamentStatus.PLANIFICADO: [
        TournamentStatus.INSCRIPCION,
        TournamentStatus.ARCHIVADO,
    ],
    TournamentStatus.INSCRIPCION: [
        TournamentStatus.VERIFICACION,
        TournamentStatus.PLANIFICADO,
    ],
    TournamentStatus.VERIFICACION: [
        TournamentStatus.EN_CURSO,
    ],
    TournamentStatus.EN_CURSO: [
        TournamentStatus.FINALIZADO,
    ],
    TournamentStatus.FINALIZADO: [
        TournamentStatus.ARCHIVADO,
    ],
    # ARCHIVADO es estado terminal — sin transiciones salientes
    TournamentStatus.ARCHIVADO: [],
}

# Mínimo de árbitros requeridos para iniciar competencia (WKF 2026)
MIN_ARBITERS_REQUIRED = 3
# Mínimo de atletas por categoría para bracket válida (WKF 2026)
MIN_ATHLETES_PER_CATEGORY = 2


# =============================================================================
# DATA CLASSES — Resultados expresivos
# =============================================================================


@dataclass
class ValidationResult:
    """Resultado de validación de pre-condiciones."""

    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TransitionResult:
    """Resultado de una transición de estado."""

    success: bool
    tournament_id: int
    old_status: TournamentStatus
    new_status: Optional[TournamentStatus] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


# =============================================================================
# TOURNAMENT SERVICE
# =============================================================================


class TournamentService:
    """
    Servicio de gestión de transiciones de estado de torneos.

    Centraliza toda la lógica de negocio (validaciones y transiciones)
    siguiendo el patrón AuthService. TournamentState consume este servicio
    para exponer event handlers a la UI.
    """

    @staticmethod
    def _log_failed_attempt(
        tournament_id: int,
        user_id: int,
        old_status: "TournamentStatus",
        new_status: Optional["TournamentStatus"],
        reason: str,
    ) -> None:
        """
        Registra en audit log un intento de transición fallido.

        Se usa para auditoría de seguridad (spec req 13: SHOULD loguear
        intentos de transición inválida).

        Args:
            tournament_id: ID del torneo.
            user_id: ID del usuario que intentó la transición.
            old_status: Estado actual del torneo.
            new_status: Estado destino intentado (puede ser None).
            reason: Código de razón del fallo (ej: INVALID_TRANSITION, TERMINAL_STATE).
        """
        try:
            with rx.session() as session:
                log = TournamentEventLog(
                    tournament_id=tournament_id,
                    user_id=user_id,
                    event_type="TRANSITION_ATTEMPT_FAILED",
                    old_status=old_status.value,
                    new_status=new_status.value if new_status else None,
                    details=reason,
                )
                session.add(log)
                session.commit()
        except Exception:
            # No propagar errores de logging — el fallo principal ya fue retornado
            pass

    @staticmethod
    def can_transition(
        from_status: TournamentStatus,
        to_status: TournamentStatus,
    ) -> bool:
        """
        Verifica si una transición entre dos estados es válida según WKF 2026.

        Args:
            from_status: Estado actual del torneo.
            to_status: Estado destino solicitado.

        Returns:
            True si la transición está permitida, False en caso contrario.
        """
        allowed = VALID_TRANSITIONS.get(from_status, [])
        return to_status in allowed

    @staticmethod
    def _validate_verificacion(
        tournament_id: int,
    ) -> List[ValidationError]:
        """Valida pre-condiciones para INSCRIPCION → VERIFICACION."""
        errors: List[ValidationError] = []
        with rx.session() as session:
            categories = session.exec(
                select(TournamentCategory).where(
                    TournamentCategory.tournament_id == tournament_id
                )
            ).all()
        if len(categories) == 0:
            errors.append(
                ValidationError(
                    code="NO_CATEGORIES",
                    message="Debe crear al menos 1 categoría antes de verificar",
                    current_value=0,
                    required_value=1,
                )
            )
        return errors

    @staticmethod
    def _validate_en_curso(
        tournament_id: int,
    ) -> tuple[List[ValidationError], List[str]]:
        """Valida pre-condiciones para VERIFICACION → EN_CURSO."""
        from kakumi_app.models.athlete_model import Athlete, AthleteGender
        from kakumi_app.models.tournament_model import CategoryGender
        from kakumi_app.utils import BELT_RANKS, BELT_RANK_ORDER

        errors: List[ValidationError] = []
        warnings: List[str] = []

        with rx.session() as session:
            categories = session.exec(
                select(TournamentCategory).where(
                    TournamentCategory.tournament_id == tournament_id
                )
            ).all()

            for category in categories:
                query = select(Athlete).where(
                    Athlete.age.between(category.min_age, category.max_age)
                )
                if category.gender == CategoryGender.MALE.value:
                    query = query.where(Athlete.gender == AthleteGender.MALE.value)
                elif category.gender == CategoryGender.FEMALE.value:
                    query = query.where(Athlete.gender == AthleteGender.FEMALE.value)

                athletes = session.exec(query).all()

                if category.min_belt_rank or category.max_belt_rank:
                    min_idx = BELT_RANK_ORDER.get(category.min_belt_rank, 0)
                    max_idx = BELT_RANK_ORDER.get(
                        category.max_belt_rank, len(BELT_RANKS) - 1
                    )
                    athletes = [
                        a
                        for a in athletes
                        if a.belt_rank
                        and min_idx <= BELT_RANK_ORDER.get(a.belt_rank, -1) <= max_idx
                    ]

                total_athletes = len(athletes)

                if total_athletes < MIN_ATHLETES_PER_CATEGORY:
                    errors.append(
                        ValidationError(
                            code="INSUFFICIENT_ATHLETES",
                            message=(
                                f"Categoría {category.name!r} tiene "
                                f"{total_athletes} atletas, mínimo "
                                f"requerido: {MIN_ATHLETES_PER_CATEGORY}"
                            ),
                            category_name=category.name,
                            current_value=total_athletes,
                            required_value=MIN_ATHLETES_PER_CATEGORY,
                        )
                    )

            available_referees = session.exec(
                select(Referee).where(Referee.is_available == True)  # noqa: E712
            ).all()
            referee_count = len(available_referees)

            tournament = session.get(Tournament, tournament_id)
            has_schedule = bool(tournament and tournament.start_date)

        if referee_count < MIN_ARBITERS_REQUIRED:
            errors.append(
                ValidationError(
                    code="NO_ARBITERS",
                    message=(
                        f"Se requieren mínimo {MIN_ARBITERS_REQUIRED} árbitros, "
                        f"disponibles: {referee_count}"
                    ),
                    current_value=referee_count,
                    required_value=MIN_ARBITERS_REQUIRED,
                )
            )

        if not has_schedule:
            warnings.append("El horario del torneo no está configurado")

        return errors, warnings

    @staticmethod
    def _generate_brackets_for_tournament(tournament_id: int) -> None:
        # ponytail: separate session from transition_to parent session.
        # Creates minor TOCTOU if a category is added between lock and here.
        # Acceptable for MVP — consolidate sessions if category races arise.
        with rx.session() as session:
            categories = session.exec(
                select(TournamentCategory).where(
                    TournamentCategory.tournament_id == tournament_id
                )
            ).all()
            for category in categories:
                if category.competition_system not in {
                    CompetitionSystem.ELIMINATION.value,
                    CompetitionSystem.ROUND_ROBIN.value,
                }:
                    continue
                try:
                    generate_bracket(
                        tournament_id=tournament_id,
                        category_id=category.id,
                        session=session,
                    )
                except ValidationError as exc:
                    if exc.code == "BRACKET_ALREADY_EXISTS":
                        continue
                    raise

    @staticmethod
    def _validate_finalizado(
        tournament_id: int,
    ) -> List[ValidationError]:
        """Valida pre-condiciones para EN_CURSO → FINALIZADO."""
        errors: List[ValidationError] = []
        with rx.session() as session:
            categories = session.exec(
                select(TournamentCategory).where(
                    TournamentCategory.tournament_id == tournament_id
                )
            ).all()
            informal_category_ids = [
                category.id
                for category in categories
                if str(getattr(category, "kata_flow_mode", "STANDARD")) == "INFORMAL"
            ]
            standard_category_ids = [
                category.id
                for category in categories
                if category.id not in informal_category_ids
            ]

            if standard_category_ids:
                incomplete_matches = session.exec(
                    select(Match).where(
                        Match.category_id.in_(standard_category_ids),
                        Match.status != MatchStatus.COMPLETED.value,
                    )
                ).all()
                incomplete_count = len(incomplete_matches)

                if incomplete_count > 0:
                    errors.append(
                        ValidationError(
                            code="MATCHES_INCOMPLETE",
                            message=(
                                f"Existen {incomplete_count} matches sin completar"
                            ),
                            current_value=incomplete_count,
                            required_value=0,
                        )
                    )

            for category in categories:
                if category.id not in informal_category_ids:
                    continue
                if category.status != CategoryStatus.COMPLETED.value:
                    errors.append(
                        ValidationError(
                            code="INFORMAL_CATEGORY_INCOMPLETE",
                            message=(
                                f"Categoría informal {category.name!r} no está "
                                "completada"
                            ),
                            category_name=category.name,
                            current_value=category.status,
                            required_value=CategoryStatus.COMPLETED.value,
                        )
                    )
                    continue
                if (
                    category.first_place_id is None
                    or category.second_place_id is None
                    or not category.third_place_ids
                ):
                    errors.append(
                        ValidationError(
                            code="INFORMAL_PODIUM_INCOMPLETE",
                            message=(
                                f"Categoría informal {category.name!r} no tiene podio "
                                "completo"
                            ),
                            category_name=category.name,
                        )
                    )
        return errors

    @staticmethod
    def validate_preconditions(
        tournament_id: int,
        to_status: TournamentStatus,
    ) -> ValidationResult:
        """
        Valida las pre-condiciones requeridas antes de ejecutar una transición.

        Permite modo dry-run — no modifica el estado del torneo.
        Los errores REQUIRED bloquean la transición.
        Los warnings se incluyen pero no bloquean.

        Args:
            tournament_id: ID del torneo a validar.
            to_status: Estado destino para el cual validar las pre-condiciones.

        Returns:
            ValidationResult con errores y warnings detallados.
        """
        errors: List[ValidationError] = []
        warnings: List[str] = []

        if to_status == TournamentStatus.VERIFICACION:
            errors = TournamentService._validate_verificacion(tournament_id)
        elif to_status == TournamentStatus.EN_CURSO:
            errors, warnings = TournamentService._validate_en_curso(tournament_id)
        elif to_status == TournamentStatus.FINALIZADO:
            errors = TournamentService._validate_finalizado(tournament_id)
        # Para INSCRIPCION, PLANIFICADO y ARCHIVADO: sin pre-condiciones requeridas

        is_valid = len(errors) == 0
        return ValidationResult(
            valid=is_valid,
            errors=errors,
            warnings=warnings,
        )

    @staticmethod
    def transition_to(
        tournament_id: int,
        new_status: TournamentStatus,
        user_id: int,
        dry_run: bool = False,
    ) -> TransitionResult:
        """
        Ejecuta una transición de estado con validación completa y audit log.

        Flujo:
        1. Cargar el torneo desde DB
        2. Verificar que no hay transición en progreso (is_transitioning)
        3. Verificar que la transición es válida (VALID_TRANSITIONS)
        4. Verificar pre-condiciones de negocio
        5. Si dry_run=True, retornar resultado sin ejecutar
        6. Setear is_transitioning=True (lock)
        7. Actualizar estado en DB
        8. Crear audit log
        9. Liberar lock (is_transitioning=False)
        10. Retornar TransitionResult exitoso

        Args:
            tournament_id: ID del torneo a transicionar.
            new_status: Estado destino.
            user_id: ID del usuario que ejecuta la transición (para audit).
            dry_run: Si True, valida sin ejecutar cambios.

        Returns:
            TransitionResult con resultado de la operación.
        """
        # 1. Cargar torneo
        with rx.session() as session:
            tournament = session.get(Tournament, tournament_id)
            if not tournament:
                return TransitionResult(
                    success=False,
                    tournament_id=tournament_id,
                    old_status=TournamentStatus.PLANIFICADO,  # placeholder
                    new_status=None,
                    error_code="TOURNAMENT_NOT_FOUND",
                    error_message=f"Torneo con ID {tournament_id} no encontrado",
                )

            old_status_value = tournament.status
            is_currently_transitioning = tournament.is_transitioning

        # Convertir string a enum para comparación
        try:
            old_status = TournamentStatus(old_status_value)
        except ValueError:
            return TransitionResult(
                success=False,
                tournament_id=tournament_id,
                old_status=TournamentStatus.PLANIFICADO,
                new_status=None,
                error_code="INVALID_CURRENT_STATE",
                error_message=f"Estado actual inválido: {old_status_value!r}",
            )

        # 2. Verificar lock de transición
        if is_currently_transitioning:
            return TransitionResult(
                success=False,
                tournament_id=tournament_id,
                old_status=old_status,
                new_status=None,
                error_code="TRANSITION_IN_PROGRESS",
                error_message=(
                    "Ya hay una transición en progreso para este torneo. "
                    "Intenta nuevamente en unos segundos."
                ),
            )

        # 3. Verificar que la transición es válida (tabla WKF)
        if old_status == TournamentStatus.ARCHIVADO:
            # Loguear intento desde estado terminal
            TournamentService._log_failed_attempt(
                tournament_id=tournament_id,
                user_id=user_id,
                old_status=old_status,
                new_status=new_status,
                reason="TERMINAL_STATE",
            )
            return TransitionResult(
                success=False,
                tournament_id=tournament_id,
                old_status=old_status,
                new_status=None,
                error_code="TERMINAL_STATE",
                error_message=(
                    "El estado ARCHIVADO es terminal — no se pueden ejecutar "
                    "más transiciones desde este estado."
                ),
            )

        if not TournamentService.can_transition(old_status, new_status):
            valid_targets = [s.value for s in VALID_TRANSITIONS.get(old_status, [])]
            # Loguear intento de transición inválida
            TournamentService._log_failed_attempt(
                tournament_id=tournament_id,
                user_id=user_id,
                old_status=old_status,
                new_status=new_status,
                reason="INVALID_TRANSITION",
            )
            return TransitionResult(
                success=False,
                tournament_id=tournament_id,
                old_status=old_status,
                new_status=None,
                error_code="INVALID_TRANSITION",
                error_message=(
                    f"No se puede transicionar de {old_status.value} a "
                    f"{new_status.value}. "
                    f"Transiciones válidas: {valid_targets}"
                ),
            )

        # 4. Validar pre-condiciones de negocio
        validation = TournamentService.validate_preconditions(
            tournament_id=tournament_id,
            to_status=new_status,
        )
        if not validation.valid:
            error_msgs = "; ".join(e.message for e in validation.errors)
            return TransitionResult(
                success=False,
                tournament_id=tournament_id,
                old_status=old_status,
                new_status=None,
                error_code=validation.errors[0].code
                if validation.errors
                else "VALIDATION_FAILED",
                error_message=error_msgs,
                warnings=validation.warnings,
            )

        # 5. dry_run — retornar sin ejecutar
        if dry_run:
            return TransitionResult(
                success=True,
                tournament_id=tournament_id,
                old_status=old_status,
                new_status=new_status,
                warnings=validation.warnings,
            )

        # 6-9. Ejecutar transición con lock
        with rx.session() as session:
            tournament = session.get(Tournament, tournament_id)
            if not tournament:
                return TransitionResult(
                    success=False,
                    tournament_id=tournament_id,
                    old_status=old_status,
                    new_status=None,
                    error_code="TOURNAMENT_NOT_FOUND",
                    error_message="Torneo no encontrado durante la transición",
                )

            # Lock
            tournament.is_transitioning = True
            session.add(tournament)
            session.commit()

            try:
                # Actualizar estado
                TournamentService._generate_brackets_for_tournament(tournament_id)
                tournament.status = new_status.value
                tournament.is_transitioning = False
                session.add(tournament)

                # Crear audit log
                audit_log = TournamentEventLog(
                    tournament_id=tournament_id,
                    user_id=user_id,
                    event_type="STATUS_CHANGE",
                    old_status=old_status.value,
                    new_status=new_status.value,
                    details=(f"Transición de {old_status.value} a {new_status.value}"),
                )
                session.add(audit_log)
                session.commit()

            except Exception as exc:
                # Liberar lock en caso de error
                session.rollback()
                tournament.is_transitioning = False
                session.add(tournament)
                session.commit()
                return TransitionResult(
                    success=False,
                    tournament_id=tournament_id,
                    old_status=old_status,
                    new_status=None,
                    error_code="DB_ERROR",
                    error_message=str(exc),
                )

        return TransitionResult(
            success=True,
            tournament_id=tournament_id,
            old_status=old_status,
            new_status=new_status,
            warnings=validation.warnings,
        )
