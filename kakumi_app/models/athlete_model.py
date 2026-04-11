"""
KAKUMI
Módulo de modelo de atleta.
Implementación según specs.md sección 2.1.
"""

import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

import reflex as rx
from sqlmodel import Field, Relationship

if TYPE_CHECKING:
    from .team_model import TeamMember
    from .tournament_model import Match, TournamentCategory


class AthleteGender(str, Enum):
    """Género del atleta."""

    MALE = "MALE"
    FEMALE = "FEMALE"


class Athlete(rx.Model, table=True):
    """
    Modelo de Atleta para competiciones de Karate-Do.

    Un atleta puede participar en categorías de Kata y Kumite,
    y puede ser miembro de múltiples equipos mediante TeamMember.
    """

    __tablename__ = "athletes"

    # Campos obligatorios
    name: str = Field(unique=True, index=True, max_length=255)
    date_of_birth: datetime.date = Field(index=True)
    gender: str = Field(max_length=10)  # MALE, FEMALE

    # Campos opcionales según spec 2.1
    email: Optional[str] = Field(default=None, unique=True, max_length=255)
    weight_kg: Optional[float] = Field(default=None)  # 40.0 - 120.0
    belt_rank: Optional[str] = Field(default=None, max_length=50)  # "Kyu 1" - "Dan 10"
    dojo: Optional[str] = Field(default=None, max_length=255)
    nationality: Optional[str] = Field(default=None, max_length=3)  # ISO 3166-1 alpha-3
    license_number: Optional[str] = Field(default=None, unique=True, max_length=50)

    # Estado
    is_active: bool = Field(default=True)

    # Foreign Keys para categorías (relación opcional)
    kata_category_id: Optional[int] = Field(
        default=None, foreign_key="tournament_categories.id"
    )
    kumite_category_id: Optional[int] = Field(
        default=None, foreign_key="tournament_categories.id"
    )

    # Timestamps
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.datetime.utcnow},
    )

    # Relaciones
    kata_category: Optional["TournamentCategory"] = Relationship(
        back_populates="athletes",
        sa_relationship_kwargs={"foreign_keys": "[Athlete.kata_category_id]"},
    )
    kumite_category: Optional["TournamentCategory"] = Relationship(
        back_populates="kumite_athletes",
        sa_relationship_kwargs={"foreign_keys": "[Athlete.kumite_category_id]"},
    )
    team_memberships: List["TeamMember"] = Relationship(back_populates="athlete")

    # Relaciones inversas con Match (navegación bidireccional)
    matches_as_aka: List["Match"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Match.aka_id]"},
    )
    matches_as_ao: List["Match"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Match.ao_id]"},
    )
    matches_won: List["Match"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Match.winner_id]"},
    )
