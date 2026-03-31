"""
Tournament Service
Business logic for tournament state transitions and validation.
"""

import datetime
from typing import Dict, List, Optional, Tuple

import reflex as rx
from sqlmodel import select

from kakumi_app.models.tournament_model import Tournament, TournamentStatus


class TournamentService:
    """Service for tournament operations."""

    @staticmethod
    def get_all_tournaments() -> List[Tournament]:
        """Retrieve all tournaments."""
        with rx.session() as session:
            return session.exec(select(Tournament)).all()

    @staticmethod
    def get_tournament_by_id(tournament_id: int) -> Optional[Tournament]:
        """Retrieve a tournament by ID."""
        with rx.session() as session:
            return session.get(Tournament, tournament_id)

    @staticmethod
    def create_tournament(
        name: str,
        date: Optional[datetime.date] = None,
    ) -> Tournament:
        """Create a new tournament with default status PLANIFICADO."""
        with rx.session() as session:
            tournament = Tournament(
                name=name,
                date=date or datetime.date.today(),
                status=TournamentStatus.PLANIFICADO,
            )
            session.add(tournament)
            session.commit()
            session.refresh(tournament)
            return tournament

    @staticmethod
    def update_tournament(
        tournament_id: int, updates: Dict[str, any]
    ) -> Optional[Tournament]:
        """Update tournament fields."""
        with rx.session() as session:
            tournament = session.get(Tournament, tournament_id)
            if not tournament:
                return None
            for key, value in updates.items():
                if hasattr(tournament, key):
                    setattr(tournament, key, value)
            session.add(tournament)
            session.commit()
            session.refresh(tournament)
            return tournament

    @staticmethod
    def delete_tournament(tournament_id: int) -> bool:
        """Delete a tournament."""
        with rx.session() as session:
            tournament = session.get(Tournament, tournament_id)
            if not tournament:
                return False
            session.delete(tournament)
            session.commit()
            return True

    @staticmethod
    def validate_status_transition(
        current_status: TournamentStatus, new_status: TournamentStatus
    ) -> Tuple[bool, str]:
        """
        Validate if a status transition is allowed.
        Returns (is_valid, error_message).
        """
        # Define allowed transitions
        allowed_transitions: Dict[TournamentStatus, List[TournamentStatus]] = {
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
                TournamentStatus.INSCRIPCION,
            ],
            TournamentStatus.EN_CURSO: [
                TournamentStatus.FINALIZADO,
                TournamentStatus.VERIFICACION,
            ],
            TournamentStatus.FINALIZADO: [
                TournamentStatus.ARCHIVADO,
                TournamentStatus.EN_CURSO,
            ],
            TournamentStatus.ARCHIVADO: [
                TournamentStatus.PLANIFICADO,
            ],
        }
        if new_status in allowed_transitions.get(current_status, []):
            return True, ""
        return (
            False,
            f"Transition from {current_status.value} to {new_status.value} is not allowed.",
        )

    @staticmethod
    def change_tournament_status(
        tournament_id: int, new_status: TournamentStatus
    ) -> Tuple[Optional[Tournament], str]:
        """
        Change tournament status with validation.
        Returns (tournament, error_message).
        """
        with rx.session() as session:
            tournament = session.get(Tournament, tournament_id)
            if not tournament:
                return None, "Tournament not found."
            is_valid, error = TournamentService.validate_status_transition(
                tournament.status, new_status
            )
            if not is_valid:
                return None, error
            tournament.status = new_status
            session.add(tournament)
            session.commit()
            session.refresh(tournament)
            return tournament, ""

    @staticmethod
    def open_inscriptions(tournament_id: int) -> Tuple[Optional[Tournament], str]:
        """Open inscriptions for a tournament (PLANIFICADO -> INSCRIPCION)."""
        return TournamentService.change_tournament_status(
            tournament_id, TournamentStatus.INSCRIPCION
        )

    @staticmethod
    def close_inscriptions(tournament_id: int) -> Tuple[Optional[Tournament], str]:
        """Close inscriptions and move to verification (INSCRIPCION -> VERIFICACION)."""
        return TournamentService.change_tournament_status(
            tournament_id, TournamentStatus.VERIFICACION
        )

    @staticmethod
    def start_competition(tournament_id: int) -> Tuple[Optional[Tournament], str]:
        """Start competition (VERIFICACION -> EN_CURSO)."""
        return TournamentService.change_tournament_status(
            tournament_id, TournamentStatus.EN_CURSO
        )

    @staticmethod
    def finish_tournament(tournament_id: int) -> Tuple[Optional[Tournament], str]:
        """Finish tournament (EN_CURSO -> FINALIZADO)."""
        return TournamentService.change_tournament_status(
            tournament_id, TournamentStatus.FINALIZADO
        )

    @staticmethod
    def archive_tournament(tournament_id: int) -> Tuple[Optional[Tournament], str]:
        """Archive tournament (FINALIZADO -> ARCHIVADO)."""
        return TournamentService.change_tournament_status(
            tournament_id, TournamentStatus.ARCHIVADO
        )

    @staticmethod
    def reset_tournament(tournament_id: int) -> Tuple[Optional[Tournament], str]:
        """Reset tournament to PLANIFICADO (if allowed)."""
        return TournamentService.change_tournament_status(
            tournament_id, TournamentStatus.PLANIFICADO
        )
