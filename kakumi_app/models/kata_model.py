"""Modelos y contratos de scoring Kata bajo WKF 2026."""

import datetime
from enum import Enum
from typing import Optional

import reflex as rx
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
