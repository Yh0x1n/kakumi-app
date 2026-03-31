"""
KAKUMI
Módulo de modelo de puntuación de encuentro
"""

import datetime
from typing import TYPE_CHECKING, Optional

import reflex as rx
from sqlmodel import Field, Relationship, func

if TYPE_CHECKING:
    from .match_model import Match
    from .referee_model import Referee


class MatchScore(rx.Model, table=True):
    match_id: int = Field(foreign_key="match.id")
    participant: str  # AKA / AO
    judge_id: int = Field(foreign_key="referee.id")
    score_value: float
    score_type: str  # IPPON / WAZA_ARI / YUKO / PENALTY / WARNING
    technique_time: Optional[int] = None
    is_valid: bool = Field(default=False)
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        sa_column_kwargs={"server_default": func.now()},
    )

    # Relaciones
    match: "Match" = Relationship(back_populates="scores")
    judge: "Referee" = Relationship()
