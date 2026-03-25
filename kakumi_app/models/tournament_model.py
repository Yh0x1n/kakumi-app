import datetime
from typing import List, Optional

import reflex as rx
from sqlmodel import Field, Relationship

from .athlete_model import Athlete


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
    status: str = "Planificado"

    # Relaciones que apuntan a cada clase hija por separado
    kata_categories: List[KataCategory] = Relationship(back_populates="tournament")
    kumite_categories: List[KumiteCategory] = Relationship(back_populates="tournament")


class Match(rx.Model, table=True):
    """Modelo para representar los resultados de un encuentro."""

    id: Optional[int] = Field(default=None, primary_key=True)

    # 1. Llaves Foráneas a Atletas (Aka y Ao)
    aka_id: int = Field(foreign_key="athlete.id")
    ao_id: int = Field(foreign_key="athlete.id")

    # 2. Resultados del Encuentro
    aka_score: int = Field(default=0)
    ao_score: int = Field(default=0)
    winner_id: Optional[int] = Field(default=None, foreign_key="athlete.id")

    # 3. Vínculo con la Categoría
    kata_category_id: Optional[int] = Field(default=None, foreign_key="katacategory.id")
    kumite_category_id: Optional[int] = Field(
        default=None, foreign_key="kumitecategory.id"
    )

    # 4. Relaciones (Acceso directo a objetos)

    aka: "Athlete" = Relationship(
        sa_relationship_kwargs={"primaryjoin": "Match.aka_id == Athlete.id"}
    )
    ao: "Athlete" = Relationship(
        sa_relationship_kwargs={"primaryjoin": "Match.ao_id == Athlete.id"}
    )

    # Relaciones con las categorías
    kata_category: Optional["KataCategory"] = Relationship()
    kumite_category: Optional["KumiteCategory"] = Relationship()
