"""Custom exceptions for the penalty and scheduling system."""


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
