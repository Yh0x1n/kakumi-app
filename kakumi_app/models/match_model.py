"""
KAKUMI
Módulo de modelo de encuentro (match)
"""

import datetime
from typing import TYPE_CHECKING, List, Optional

import reflex as rx
from sqlmodel import Field, Relationship, func, CheckConstraint

if TYPE_CHECKING:
    from .tournament_model import KataCategory, KumiteCategory
    from .athlete_model import Athlete
    from .referee_model import Referee
    from .tournament_area_model import TournamentArea
    from .penalty_model import Penalty
    from .match_score_model import MatchScore


class Match(rx.Model, table=True):
    # Nota: La spec indica category_id, pero el diseño actual tiene dos tablas de categoría.
    # Usamos ambas foreign keys y garantizamos que al menos una sea no nula.
    kata_category_id: Optional[int] = Field(default=None, foreign_key="katacategory.id")
    kumite_category_id: Optional[int] = Field(
        default=None, foreign_key="kumitecategory.id"
    )
    round: int
    match_number: int
    position: int
    match_type: str  # ELIMINATION / BRONZE / FINAL / ROUND_ROBIN
    aka_id: int = Field(foreign_key="athlete.id")
    ao_id: int = Field(foreign_key="athlete.id")
    aka_score: int = Field(default=0)
    ao_score: int = Field(default=0)
    winner_id: Optional[int] = Field(default=None, foreign_key="athlete.id")
    status: str = Field(
        default="PENDING"
    )  # PENDING / READY / IN_PROGRESS / COMPLETED / DISQUALIFIED
    start_time: Optional[datetime.datetime] = None
    end_time: Optional[datetime.datetime] = None
    tatami_id: Optional[int] = Field(default=None, foreign_key="tournamentarea.id")
    referee_id: Optional[int] = Field(default=None, foreign_key="referee.id")
    judge_panel_id: Optional[int] = None  # TODO: crear modelo para panel de jueces
    notes: Optional[str] = None
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        sa_column_kwargs={"server_default": func.now()},
    )

    # Relaciones
    kata_category: Optional["KataCategory"] = Relationship()
    kumite_category: Optional["KumiteCategory"] = Relationship()
    aka: "Athlete" = Relationship(
        sa_relationship_kwargs={"primaryjoin": "Match.aka_id == Athlete.id"}
    )
    ao: "Athlete" = Relationship(
        sa_relationship_kwargs={"primaryjoin": "Match.ao_id == Athlete.id"}
    )
    winner: Optional["Athlete"] = Relationship(
        sa_relationship_kwargs={"primaryjoin": "Match.winner_id == Athlete.id"}
    )
    tatami: Optional["TournamentArea"] = Relationship(back_populates="current_match")
    referee: Optional["Referee"] = Relationship()
    penalties: List["Penalty"] = Relationship(back_populates="match")
    scores: List["MatchScore"] = Relationship(back_populates="match")

    # Constraint a nivel de tabla para asegurar al menos una categoría
    __table_args__ = (
        CheckConstraint(
            "(kata_category_id IS NOT NULL) OR (kumite_category_id IS NOT NULL)",
            name="match_category_check",
        ),
    )

    @property
    def category_id(self) -> int:
        """Devuelve el id de la categoría correspondiente (kata o kumite)."""
        return self.kata_category_id or self.kumite_category_id
