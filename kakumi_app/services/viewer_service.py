"""
Viewer Service
Business logic for viewer access codes and validation.
"""

import secrets
from typing import Optional
import datetime

import reflex as rx
from sqlmodel import select

from kakumi_app.models.tournament_model import Tournament


class ViewerService:
    """Service for viewer access operations."""

    EXPIRATION_HOURS = 5  # Viewer codes expire after 5 hours
    _MAX_ATTEMPTS = 5
    _LOCKOUT_MINUTES = 5
    # In-memory store for failed attempts per code
    _failed_attempts: dict[str, tuple[int, datetime.datetime]] = {}

    @staticmethod
    def _is_code_expired(tournament: Tournament) -> bool:
        """Return True if the viewer code has expired."""
        if tournament.viewer_code_generated_at is None:
            # NULL timestamp — treat as expired
            return True
        age = datetime.datetime.utcnow() - tournament.viewer_code_generated_at
        return age.total_seconds() > ViewerService.EXPIRATION_HOURS * 3600

    @staticmethod
    def _is_code_locked(code: str) -> bool:
        """Check if the code is locked due to too many failed attempts."""
        if code not in ViewerService._failed_attempts:
            return False
        attempts, last_attempt = ViewerService._failed_attempts[code]
        if attempts < ViewerService._MAX_ATTEMPTS:
            return False
        # Check if lockout period has passed
        lockout_seconds = ViewerService._LOCKOUT_MINUTES * 60
        elapsed = (datetime.datetime.utcnow() - last_attempt).total_seconds()
        if elapsed > lockout_seconds:
            # Lockout expired, reset attempts
            del ViewerService._failed_attempts[code]
            return False
        return True

    @staticmethod
    def _record_failed_attempt(code: str) -> None:
        """Record a failed validation attempt for the given code."""
        now = datetime.datetime.utcnow()
        if code not in ViewerService._failed_attempts:
            ViewerService._failed_attempts[code] = (1, now)
        else:
            attempts, _ = ViewerService._failed_attempts[code]
            ViewerService._failed_attempts[code] = (attempts + 1, now)

    @staticmethod
    def _reset_attempts(code: str) -> None:
        """Reset failed attempts for a code after successful validation."""
        if code in ViewerService._failed_attempts:
            del ViewerService._failed_attempts[code]

    @staticmethod
    def generate_viewer_code(tournament_id: int) -> Optional[str]:
        """Generate a new viewer code for a tournament and save it.

        Returns the generated code, or None if tournament not found.
        """
        with rx.session() as session:
            tournament = session.get(Tournament, tournament_id)
            if not tournament:
                return None
            new_code = secrets.token_hex(4)
            tournament.viewer_code = new_code
            tournament.viewer_code_generated_at = datetime.datetime.utcnow()
            session.add(tournament)
            session.commit()
            session.refresh(tournament)
            return new_code

    @staticmethod
    def validate_viewer_code(code: str) -> Optional[Tournament]:
        """Return tournament for a valid, unlocked, non-expired viewer code."""
        if ViewerService._is_code_locked(code):
            return None
        with rx.session() as session:
            statement = select(Tournament).where(Tournament.viewer_code == code)
            tournament = session.exec(statement).first()
            if tournament is None:
                ViewerService._record_failed_attempt(code)
                return None
            if ViewerService._is_code_expired(tournament):
                # Code expired, invalidate it
                ViewerService._record_failed_attempt(code)
                return None
            # Success, reset attempts
            ViewerService._reset_attempts(code)
            return tournament

    @staticmethod
    def check_viewer_access(code: str, tournament_id: int) -> bool:
        """Check if the viewer code grants access to the specified tournament."""
        tournament = ViewerService.validate_viewer_code(code)
        return tournament is not None and tournament.id == tournament_id

    @staticmethod
    def get_tournament_by_viewer_code(code: str) -> Optional[Tournament]:
        """Alias for validate_viewer_code for clarity."""
        return ViewerService.validate_viewer_code(code)
