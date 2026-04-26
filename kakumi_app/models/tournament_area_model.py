"""
KAKUMI
Módulo de modelo de tatami (área de torneo)
"""

from typing import TYPE_CHECKING, Optional

import reflex as rx
from sqlmodel import Field, Relationship

if TYPE_CHECKING:
    from .tournament_model import Tournament
    from .match_model import Match


class TournamentArea(rx.Model, table=True):
    tournament_id: int = Field(foreign_key="tournament.id")
    name: str = Field(max_length=50)
    location: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    current_match_id: Optional[int] = Field(default=None, foreign_key="match.id")

    # Relaciones
    tournament: "Tournament" = Relationship(back_populates="areas")
    current_match: Optional["Match"] = Relationship()
