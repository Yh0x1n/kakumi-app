"""Modelos y contratos de scoring Kata bajo WKF 2026."""

import datetime
from enum import Enum
from typing import Optional

import reflex as rx
import sqlalchemy as sa
from sqlmodel import Field


class FlagVote(str, Enum):
    """Voto por bandera en modo contingencia."""

    AKA = "AKA"
    AO = "AO"


class BunkaiMode(str, Enum):
    """Configuración de obligatoriedad de Bunkai."""

    NONE = "NONE"
    MEDALS_ONLY = "MEDALS_ONLY"
    ALL_ROUNDS = "ALL_ROUNDS"


class KataScoringMode(str, Enum):
    """Modos de scoring disponibles para Kata."""

    NUMERICAL = "NUMERICAL"
    FLAG = "FLAG"


class KataDecisionRule(str, Enum):
    """Regla de decisión para ganador numérico en Kata."""

    AVERAGE_WITH_DISCARD = "average-with-discard"
    MAJORITY_BY_JUDGE = "majority-by-judge"


class KataScoreValidationError(Exception):
    """Score fuera de rango permitido para Kata."""


class KataDuplicateScoreError(Exception):
    """Mismo juez intentó puntuar dos veces mismo lado."""


class KataJudgeCountError(Exception):
    """Cantidad de jueces incompleta o inválida para cálculo."""


class KataJudgeScore(rx.Model, table=True):
    """Score/voto de juez para un lado de un match Kata."""

    __tablename__ = "kata_judge_scores"

    judge_id: int = Field(foreign_key="referees.id", index=True)
    match_id: int = Field(foreign_key="matches.id", index=True)
    performer_id: Optional[int] = Field(default=None, foreign_key="athletes.id")
    team_id: Optional[int] = Field(default=None, foreign_key="teams.id")
    participant: str = Field(default=FlagVote.AKA.value)
    score: float = Field(default=0.0)
    flag_vote: Optional[str] = Field(default=None)
    is_flag_mode: bool = Field(default=False)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class KataRoundStanding(rx.Model, table=True):
    """Acumulado por participante/equipo en ronda Kata."""

    __tablename__ = "kata_round_standings"

    match_id: int = Field(foreign_key="matches.id", index=True)
    athlete_id: Optional[int] = Field(default=None, foreign_key="athletes.id")
    team_id: Optional[int] = Field(default=None, foreign_key="teams.id")
    victory_points: int = Field(default=0)
    votes_received: int = Field(default=0)
    needs_extra_kata: bool = Field(default=False)


class KataInformalPerformanceStatus(str, Enum):
    """Informal Kata performance lifecycle state."""

    PENDING = "PENDING"
    SCORED = "SCORED"


class KataInformalPerformance(rx.Model, table=True):
    """Single-athlete informal Kata run with derived scoring fields."""

    __tablename__ = "kata_informal_performances"
    __table_args__ = (
        sa.Index(
            "ix_kata_informal_performances_category_athlete",
            "category_id",
            "athlete_id",
        ),
        sa.Index(
            "ix_kata_informal_performances_category_sequence",
            "category_id",
            "sequence_number",
        ),
    )

    category_id: int = Field(foreign_key="tournament_categories.id", index=True)
    athlete_id: int = Field(foreign_key="athletes.id", index=True)
    sequence_number: int = Field(default=1)
    performance_round: int = Field(default=1)
    status: str = Field(default=KataInformalPerformanceStatus.SCORED.value)
    final_score: float = Field(default=0.0)
    kept_score_sum: float = Field(default=0.0)
    highest_score: float = Field(default=0.0)
    lowest_score: float = Field(default=0.0)
    max_judge_score: float = Field(default=0.0)
    is_extra_kata: bool = Field(default=False)
    tiebreak_group: Optional[str] = Field(default=None)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.datetime.utcnow},
    )


class KataInformalJudgeScore(rx.Model, table=True):
    """Judge score rows attached to one informal performance."""

    __tablename__ = "kata_informal_judge_scores"
    __table_args__ = (
        sa.UniqueConstraint(
            "performance_id",
            "judge_id",
            name="uq_kata_informal_judge_scores_performance_judge",
        ),
    )

    performance_id: int = Field(
        foreign_key="kata_informal_performances.id",
        index=True,
    )
    judge_id: int = Field(foreign_key="referees.id", index=True)
    score: float = Field(default=0.0)
    slot_order: int = Field(default=0)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
