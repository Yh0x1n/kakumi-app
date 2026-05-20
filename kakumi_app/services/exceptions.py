"""Custom exceptions for the penalty and scheduling system."""

from dataclasses import dataclass
from typing import Any, Optional


class PenaltyError(Exception):
    """Base exception for penalty and scheduling domain errors."""


class PenaltyRemovalNotAllowedError(PenaltyError):
    """Raised when removing a penalty from a non-IN_PROGRESS match."""


class AthleteSchedulingConflictError(PenaltyError):
    """Raised when an athlete is scheduled in overlapping tatami windows."""


class PenaltyEscalationError(PenaltyError):
    """Raised when a penalty escalation fails due to invalid match state."""


class ShikkakuRevertError(PenaltyError):
    """Raised when SHIKKAKU revert cannot be executed safely."""


@dataclass
class ValidationError(Exception):
    """
    Error de validación de pre-condición.

    Incluye código de error, mensaje legible y contexto específico
    de categoría cuando aplica.
    """

    code: str
    message: str
    category_name: Optional[str] = None
    current_value: Any = None
    required_value: Any = None

    def __str__(self) -> str:
        """Return the human-readable validation message."""
        return self.message
