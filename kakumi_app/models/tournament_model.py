"""
KAKUMI
Módulo de modelos de torneo y categorías.
Gestión de torneos, categorías (Kata/Kumite), encuentros y áreas de competencia.
Implementación basada en specs.md secciones 2.3, 2.4, 2.5, 2.10.
"""

import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

import reflex as rx
from sqlmodel import Field, Relationship

from .kata_model import KataDecisionRule

if TYPE_CHECKING:
    from .athlete_model import Athlete
    from .team_model import Team
    from .referee_model import Referee
    from .user_model import User


class Modality(str, Enum):
    """Modalidades de competencia según WKF."""

    KATA_INDIVIDUAL = "KATA_INDIVIDUAL"
    KATA_TEAM = "KATA_TEAM"
    KUMITE_INDIVIDUAL = "KUMITE_INDIVIDUAL"
    KUMITE_TEAM = "KUMITE_TEAM"


class CategoryGender(str, Enum):
    """Géneros permitidos en categorías."""

    MALE = "MALE"
    FEMALE = "FEMALE"
    MIXED = "MIXED"


class CompetitionSystem(str, Enum):
    """Sistemas de competencia."""

    ROUND_ROBIN = "ROUND_ROBIN"
    ELIMINATION = "ELIMINATION"


class CategoryStatus(str, Enum):
    """Estados de categoría."""

    PENDING = "PENDING"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class KataFlowMode(str, Enum):
    """Kata flow mode for individual categories."""

    STANDARD = "STANDARD"
    INFORMAL = "INFORMAL"


class MatchType(str, Enum):
    """Tipos de encuentro según specs.md sección 2.5."""

    ELIMINATION = "ELIMINATION"
    BRONZE = "BRONZE"
    FINAL = "FINAL"
    ROUND_ROBIN = "ROUND_ROBIN"


class MatchStatus(str, Enum):
    """Estados de encuentro según specs.md sección 2.5."""

    PENDING = "PENDING"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DISQUALIFIED = "DISQUALIFIED"


class BracketSide(str, Enum):
    """Lado del bracket para doble eliminación."""

    WINNERS = "WINNERS"
    LOSERS = "LOSERS"


class Participant(str, Enum):
    """Participante en un encuentro (Aka=Rojo, Ao=Azul)."""

    AKA = "AKA"
    AO = "AO"


class ParticipantSide(str, Enum):
    """Participante incluyendo BOTH para penalizaciones."""

    AKA = "AKA"
    AO = "AO"
    BOTH = "BOTH"


class ScoreType(str, Enum):
    """Tipos de puntuación en Kumite según WKF 2026."""

    IPPON = "IPPON"
    WAZA_ARI = "WAZA_ARI"
    YUKO = "YUKO"
    KATA_SCORE = "KATA_SCORE"
    PENALTY = "PENALTY"
    WARNING = "WARNING"


class PenaltyType(str, Enum):
    """Tipos de penalización según WKF 2026."""

    CHUI = "CHUI"
    HANSOKU_CHUI = "HANSOKU_CHUI"
    HANSOKU = "HANSOKU"
    SHIKKAKU = "SHIKKAKU"


class TournamentStatus(str, Enum):
    """Estados del torneo según specs.md sección 6.1."""

    PLANIFICADO = "PLANIFICADO"
    INSCRIPCION = "INSCRIPCION"
    VERIFICACION = "VERIFICACION"
    EN_CURSO = "EN_CURSO"
    FINALIZADO = "FINALIZADO"
    ARCHIVADO = "ARCHIVADO"


# ==============================================================================
# TOURNAMENT (Sección 2.3 specs.md)
# ==============================================================================


class Tournament(rx.Model, table=True):
    """
    Modelo de Torneo principal.

    Estados: PLANIFICADO -> INSCRIPCION -> VERIFICACION -> EN_CURSO
    -> FINALIZADO -> ARCHIVADO
    """

    __tablename__ = "tournaments"

    # Campos obligatorios
    name: str = Field(unique=True, max_length=255)
    venue: str = Field(max_length=255)  # Lugar de realización
    start_date: datetime.date = Field(index=True)
    end_date: datetime.date
    tatami_count: int = Field(default=1)  # 1-8 tatamis
    scheduling_gap_seconds: int = Field(default=75)
    status: str = Field(default=TournamentStatus.PLANIFICADO.value)
    is_public: bool = Field(default=True)

    # Flag de transición en progreso (previene race conditions)
    is_transitioning: bool = Field(default=False)

    # Campos opcionales
    description: Optional[str] = Field(default=None)
    organizing_federation: Optional[str] = Field(default=None, max_length=255)
    license_number: Optional[str] = Field(default=None, max_length=50)
    viewer_code: Optional[str] = Field(default=None, max_length=8)
    viewer_code_generated_at: Optional[datetime.datetime] = Field(default=None)

    # Foreign Keys
    created_by_id: Optional[int] = Field(default=None, foreign_key="users.id")

    # Timestamps
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.datetime.utcnow},
    )

    # Relaciones
    categories: List["TournamentCategory"] = Relationship(
        back_populates="tournament",
        sa_relationship_kwargs={"foreign_keys": "[TournamentCategory.tournament_id]"},
    )
    tatamis: List["Tatami"] = Relationship(
        back_populates="tournament",
        sa_relationship_kwargs={"foreign_keys": "[Tatami.tournament_id]"},
    )
    created_by: Optional["User"] = Relationship(
        back_populates="created_tournaments",
        sa_relationship_kwargs={"foreign_keys": "[Tournament.created_by_id]"},
    )


# ==============================================================================
# TOURNAMENT CATEGORY (Sección 2.4 specs.md)
# ==============================================================================


class TournamentCategory(rx.Model, table=True):
    """
    Modelo unificado de categoría (Kata/Kumite - Individual/Team).
    Reemplaza los modelos separados KataCategory y KumiteCategory.
    """

    __tablename__ = "tournament_categories"

    # Campos obligatorios
    name: str = Field(max_length=255, index=True)
    modality: str = Field(
        default=Modality.KATA_INDIVIDUAL.value
    )  # KATA_INDIVIDUAL, etc.
    gender: str = Field(default=CategoryGender.MALE.value)  # MALE, FEMALE, MIXED
    min_age: int = Field(default=0)  # Edad mínima (inclusive)
    max_age: int = Field(default=99)  # Edad máxima (inclusive)
    competition_system: str = Field(default=CompetitionSystem.ELIMINATION.value)
    bracket_size: int = Field(default=8)  # 4, 8, 16, 32
    status: str = Field(default=CategoryStatus.PENDING.value)

    # Foreign Keys
    tournament_id: int = Field(foreign_key="tournaments.id", index=True)

    # Campos opcionales para Kata
    min_belt_rank: Optional[str] = Field(default=None, max_length=10)
    max_belt_rank: Optional[str] = Field(default=None, max_length=10)
    has_bunkai: bool = Field(default=False)
    judge_panel_size: int = Field(default=3)  # 3..7
    scoring_type: Optional[str] = Field(default=None)  # STANDARD, FLAG
    kata_decision_rule: str = Field(default=KataDecisionRule.AVERAGE_WITH_DISCARD.value)
    kata_flow_mode: str = Field(default=KataFlowMode.STANDARD.value)
    bunkai_mode: str = Field(default="NONE")

    # Campos opcionales para Kumite
    min_weight_kg: Optional[float] = Field(default=None)
    max_weight_kg: Optional[float] = Field(default=None)
    match_duration_seconds: int = Field(default=180)  # 180-300
    extension_duration_seconds: int = Field(default=60)  # 60-180
    has_weight_tolerance: bool = Field(default=False)
    weight_tolerance_kg: Optional[float] = Field(default=None)

    # Resultados (nullable hasta que finalice la categoría)
    first_place_id: Optional[int] = Field(default=None, foreign_key="athletes.id")
    second_place_id: Optional[int] = Field(default=None, foreign_key="athletes.id")
    third_place_ids: Optional[str] = Field(default=None)  # JSON array de IDs

    # Timestamps
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    # Relaciones
    tournament: "Tournament" = Relationship(
        back_populates="categories",
        sa_relationship_kwargs={"foreign_keys": "[TournamentCategory.tournament_id]"},
    )

    # Equipos (para Kata/Kumite por equipos)
    teams: List["Team"] = Relationship(
        back_populates="category",
        sa_relationship_kwargs={"foreign_keys": "[Team.category_id]"},
    )

    # Encuentros de la categoría
    matches: List["Match"] = Relationship(
        back_populates="category",
        sa_relationship_kwargs={"foreign_keys": "[Match.category_id]"},
    )


# ==============================================================================
# MATCH (Sección 2.5 specs.md)
# ==============================================================================


class Match(rx.Model, table=True):
    """
    Modelo de encuentro entre dos atletas/equipos.
    """

    __tablename__ = "matches"

    # Identificación
    round: int = Field(default=1)  # Ronda del bracket (1=primera, 2=cuartos, etc.)
    match_number: int = Field(default=1)  # Número de encuentro dentro de la ronda
    position: int = Field(default=0)  # Posición en el bracket
    match_type: str = Field(
        default=MatchType.ELIMINATION.value
    )  # ELIMINATION, BRONZE, FINAL, ROUND_ROBIN

    # Foreign Keys
    tournament_id: Optional[int] = Field(
        default=None,
        foreign_key="tournaments.id",
        index=True,
    )
    category_id: int = Field(foreign_key="tournament_categories.id", index=True)

    # Participantes (uno requerido: bye)
    aka_id: Optional[int] = Field(default=None, foreign_key="athletes.id")
    ao_id: Optional[int] = Field(default=None, foreign_key="athletes.id")
    aka_team_id: Optional[int] = Field(default=None, foreign_key="teams.id")
    ao_team_id: Optional[int] = Field(default=None, foreign_key="teams.id")

    # Resultados
    aka_score: int = Field(default=0)
    ao_score: int = Field(default=0)
    aka_senshu: bool = Field(default=False)
    ao_senshu: bool = Field(default=False)
    aka_ippon_count: int = Field(default=0)
    ao_ippon_count: int = Field(default=0)
    aka_waza_ari_count: int = Field(default=0)
    ao_waza_ari_count: int = Field(default=0)
    aka_yuko_count: int = Field(default=0)
    ao_yuko_count: int = Field(default=0)
    winner_id: Optional[int] = Field(default=None, foreign_key="athletes.id")
    bunkai_required: bool = Field(default=False)
    status: str = Field(
        default=MatchStatus.PENDING.value
    )  # PENDING, READY, IN_PROGRESS, COMPLETED, DISQUALIFIED

    # Tiempos
    start_time: Optional[datetime.datetime] = Field(default=None)
    end_time: Optional[datetime.datetime] = Field(default=None)

    # Asignaciones
    tatami_id: Optional[int] = Field(default=None, foreign_key="tatamis.id")
    referee_id: Optional[int] = Field(default=None, foreign_key="referees.id")
    judge_panel_id: Optional[int] = Field(default=None)

    # Notas
    notes: Optional[str] = Field(default=None)
    bracket_side: Optional[str] = Field(default=None, max_length=50)

    # Relaciones
    category: "TournamentCategory" = Relationship(
        back_populates="matches",
        sa_relationship_kwargs={"foreign_keys": "[Match.category_id]"},
    )

    aka: Optional["Athlete"] = Relationship(
        back_populates="matches_as_aka",
        sa_relationship_kwargs={"foreign_keys": "[Match.aka_id]"},
    )

    ao: Optional["Athlete"] = Relationship(
        back_populates="matches_as_ao",
        sa_relationship_kwargs={"foreign_keys": "[Match.ao_id]"},
    )

    winner: Optional["Athlete"] = Relationship(
        back_populates="matches_won",
        sa_relationship_kwargs={"foreign_keys": "[Match.winner_id]"},
    )

    aka_team: Optional["Team"] = Relationship(
        back_populates="matches_as_aka",
        sa_relationship_kwargs={"foreign_keys": "[Match.aka_team_id]"},
    )

    ao_team: Optional["Team"] = Relationship(
        back_populates="matches_as_ao",
        sa_relationship_kwargs={"foreign_keys": "[Match.ao_team_id]"},
    )

    tatami: Optional["Tatami"] = Relationship(
        back_populates="matches",
        sa_relationship_kwargs={"foreign_keys": "[Match.tatami_id]"},
    )

    referee: Optional["Referee"] = Relationship(
        back_populates="matches_as_referee",
        sa_relationship_kwargs={"foreign_keys": "[Match.referee_id]"},
    )

    current_tatamis: List["Tatami"] = Relationship(
        back_populates="current_match",
        sa_relationship_kwargs={"foreign_keys": "[Tatami.current_match_id]"},
    )

    # Penalizaciones del encuentro
    penalties: List["Penalty"] = Relationship(
        back_populates="match",
        sa_relationship_kwargs={"foreign_keys": "[Penalty.match_id]"},
    )

    # Puntuaciones de jueces
    scores: List["MatchScore"] = Relationship(
        back_populates="match",
        sa_relationship_kwargs={"foreign_keys": "[MatchScore.match_id]"},
    )

    # Snapshot de última acción para soporte de undo
    last_action_snapshot: Optional[str] = Field(default=None, max_length=65535)


# ==============================================================================
# MATCH SCORE (Sección 2.6 specs.md)
# ==============================================================================


class MatchScore(rx.Model, table=True):
    """
    Puntuación otorgada por un juez en un encuentro.
    """

    __tablename__ = "match_scores"

    # Foreign Keys
    match_id: int = Field(foreign_key="matches.id", index=True)
    judge_id: int = Field(foreign_key="referees.id")
    applied_by_id: Optional[int] = Field(default=None, foreign_key="users.id")

    # Datos de la puntuación
    participant: str = Field(default=Participant.AKA.value)  # AKA o AO
    score_value: float = Field(default=0.0)
    score_type: str = Field(
        default=ScoreType.YUKO.value
    )  # IPPON, WAZA_ARI, YUKO, PENALTY, WARNING
    technique_time: Optional[int] = Field(default=None)  # Segundos desde inicio
    is_valid: bool = Field(default=True)

    # Timestamp
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    # Relaciones
    match: "Match" = Relationship(
        back_populates="scores",
        sa_relationship_kwargs={"foreign_keys": "[MatchScore.match_id]"},
    )

    judge: "Referee" = Relationship(
        back_populates="scores_as_judge",
        sa_relationship_kwargs={"foreign_keys": "[MatchScore.judge_id]"},
    )

    applied_by: Optional["User"] = Relationship(
        back_populates="applied_scores",
        sa_relationship_kwargs={"foreign_keys": "[MatchScore.applied_by_id]"},
    )


# ==============================================================================
# PENALTY (Sección 2.8 specs.md)
# ==============================================================================


class Penalty(rx.Model, table=True):
    """
    Penalización aplicada en un encuentro.
    Implementa la secuencia: CHUI -> CHUI -> CHUI -> HANSOKU_CHUI -> HANSOKU
    """

    __tablename__ = "penalties"

    # Foreign Keys
    match_id: int = Field(foreign_key="matches.id", index=True)
    given_by_id: int = Field(foreign_key="referees.id")

    # Datos de la penalización
    participant: str = Field(default=ParticipantSide.AKA.value)  # AKA, AO, o BOTH
    penalty_type: str = Field(
        default=PenaltyType.CHUI.value
    )  # CHUI, HANSOKU_CHUI, HANSOKU, SHIKKAKU
    reason: str = Field(max_length=255)
    rule_reference: Optional[str] = Field(default=None, max_length=50)  # Referencia WKF
    is_accumulated: bool = Field(default=False)  # Si es por acumulación
    match_time_seconds: Optional[int] = Field(default=None)  # Tiempo cuando se impuso

    # Timestamp
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    # Relaciones
    match: "Match" = Relationship(
        back_populates="penalties",
        sa_relationship_kwargs={"foreign_keys": "[Penalty.match_id]"},
    )

    given_by: "Referee" = Relationship(
        back_populates="penalties_given",
        sa_relationship_kwargs={"foreign_keys": "[Penalty.given_by_id]"},
    )


class StandingsDeltaLog(rx.Model, table=True):
    """Audit log for SHIKKAKU standings changes, enabling safe revert."""

    __tablename__ = "standings_delta_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    athlete_id: int = Field(foreign_key="athletes.id", index=True)
    change_key: str = Field(index=True)
    before_snapshot: str = Field()
    applied_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
    )
    tournament_id: int = Field(foreign_key="tournaments.id", index=True)


# ==============================================================================
# TATAMI / TOURNAMENT AREA (Sección 2.10 specs.md)
# ==============================================================================


class Tatami(rx.Model, table=True):
    """
    Área de competencia (Tatami) dentro de un torneo.
    """

    __tablename__ = "tatamis"

    # Campos
    name: str = Field(max_length=50)  # "Tatami 1", etc.
    location: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)

    # Foreign Keys
    tournament_id: int = Field(foreign_key="tournaments.id", index=True)
    current_match_id: Optional[int] = Field(default=None, foreign_key="matches.id")

    # Relaciones
    tournament: "Tournament" = Relationship(
        back_populates="tatamis",
        sa_relationship_kwargs={"foreign_keys": "[Tatami.tournament_id]"},
    )

    current_match: Optional["Match"] = Relationship(
        back_populates="current_tatamis",
        sa_relationship_kwargs={"foreign_keys": "[Tatami.current_match_id]"},
    )

    matches: List["Match"] = Relationship(
        back_populates="tatami",
        sa_relationship_kwargs={"foreign_keys": "[Match.tatami_id]"},
    )
