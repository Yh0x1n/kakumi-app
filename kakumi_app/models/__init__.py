"""KAKUMI models package.

Paquete principal de modelos para la aplicación Kakumi de gestión
de torneos de Karate-Do. Contiene todos los modelos de datos y enums
necesarios para el sistema.

Exportaciones principales:
- Modelos de datos: Athlete, Tournament, Match, Team, Referee, User
- Enums: Modality, CategoryGender, CompetitionSystem, etc.
"""

# Importaciones de modelos principales
from .athlete_model import Athlete, AthleteGender
from .team_model import Team, TeamMember
from .tournament_model import (
    CategoryGender,
    CategoryStatus,
    CompetitionSystem,
    Match,
    MatchScore,
    MatchStatus,
    MatchType,
    Modality,
    Participant,
    ParticipantSide,
    Penalty,
    PenaltyType,
    ScoreType,
    StandingsDeltaLog,
    Tatami,
    Tournament,
    TournamentCategory,
    TournamentStatus,
)
from .referee_model import Referee
from .user_model import User
from .login_attempt import LoginAttempt
from .token_blacklist import TokenBlacklist
from .audit_log import AuditLog
from .tournament_event_log import TournamentEventLog

# Lista de exports públicos
__all__ = [
    # Modelos principales
    "Athlete",
    "AthleteGender",
    "Tournament",
    "TournamentCategory",
    "Match",
    "MatchScore",
    "Penalty",
    "StandingsDeltaLog",
    "Tatami",
    "Team",
    "TeamMember",
    "Referee",
    "User",
    "LoginAttempt",
    "TokenBlacklist",
    "AuditLog",
    "TournamentEventLog",
    # Enums de competencia
    "Modality",
    "CategoryGender",
    "CompetitionSystem",
    "CategoryStatus",
    "TournamentStatus",
    # Enums de encuentros y puntuación
    "MatchType",
    "MatchStatus",
    "Participant",
    "ParticipantSide",
    "ScoreType",
    "PenaltyType",
]

# Metadatos del paquete
__version__ = "1.0.0"
__author__ = "Kakumi Development Team"
__description__ = "Modelos de datos para gestión de torneos de Karate-Do"
