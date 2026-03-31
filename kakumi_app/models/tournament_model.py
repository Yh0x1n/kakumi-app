import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

import reflex as rx
from sqlmodel import Field, Relationship

from .athlete_model import Athlete

if TYPE_CHECKING:
    from .team_model import Team


class TournamentStatus(str, Enum):
    PLANIFICADO = "PLANIFICADO"
    INSCRIPCION = "INSCRIPCION"
    VERIFICACION = "VERIFICACION"
    EN_CURSO = "EN_CURSO"
    FINALIZADO = "FINALIZADO"
    ARCHIVADO = "ARCHIVADO"


class BaseCategory(rx.Model):
    """Clase base de las categorías"""

    name: str = Field(unique=True, index=True)
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    min_belt: Optional[int] = None
    max_belt: Optional[int] = None


class KataCategory(BaseCategory, table=True):
    """Tabla Hija de Kata"""

    id: Optional[int] = Field(default=None, primary_key=True)

    first_place: Optional[str] = None
    second_place: Optional[str] = None
    third_place: Optional[str] = None
    fourth_place: Optional[str] = None

    # Llave foránea
    tournament_id: Optional[int] = Field(default=None, foreign_key="tournament.id")

    # Relación con el campo "kata_categories" del modelo "Tournament"
    tournament: Optional["Tournament"] = Relationship(back_populates="kata_categories")
    # Relación con el campo "kata_category" del modelo "Athlete"
    athletes: List["Athlete"] = Relationship(back_populates="kata_category")
    # Relación con equipos
    teams: List["Team"] = Relationship(back_populates="category")


class KumiteCategory(BaseCategory, table=True):
    """Tabla Hija de Kumite"""

    id: Optional[int] = Field(default=None, primary_key=True)
    weight_kg: Optional[float] = None
    first_place: Optional[str] = None
    second_place: Optional[str] = None
    third_place: Optional[str] = None
    fourth_place: Optional[str] = None

    # Llave foránea
    tournament_id: Optional[int] = Field(default=None, foreign_key="tournament.id")

    # Relación con el campo "kata_categories" del modelo "Tournament"
    tournament: Optional["Tournament"] = Relationship(
        back_populates="kumite_categories"
    )
    # Relación con el campo "kumite_category" del modelo "Athlete"
    athletes: List["Athlete"] = Relationship(back_populates="kumite_category")


class Tournament(rx.Model, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    date: datetime.date = Field(default_factory=datetime.date.today)
    status: TournamentStatus = Field(default=TournamentStatus.PLANIFICADO)

    # Relaciones que apuntan a cada clase hija por separado
    kata_categories: List[KataCategory] = Relationship(back_populates="tournament")
    kumite_categories: List[KumiteCategory] = Relationship(back_populates="tournament")
