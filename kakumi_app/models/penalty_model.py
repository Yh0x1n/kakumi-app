"""
KAKUMI
Módulo de modelo de penalizaciones
"""

import datetime
from typing import TYPE_CHECKING, Optional

import reflex as rx
from sqlmodel import Field, Relationship, func

if TYPE_CHECKING:
    from .match_model import Match
    from .referee_model import Referee


class Penalty(rx.Model, table=True):
    match_id: int = Field(foreign_key="match.id")
    participant: str  # AKA / AO / BOTH
    penalty_type: str  # CHUI / KEIKOKU / HANSOKU_CHUI / HANSOKU / SHIKKAKU
    reason: str = Field(max_length=255)
    rule_reference: Optional[str] = Field(default=None, max_length=50)
    is_accumulated: bool = Field(default=False)
    given_by: int = Field(foreign_key="referee.id")
    match_time_seconds: Optional[int] = None
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        sa_column_kwargs={"server_default": func.now()},
    )

    # Relaciones
    match: "Match" = Relationship(back_populates="penalties")
    referee: "Referee" = Relationship()
