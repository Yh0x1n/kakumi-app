"""
KAKUMI
Módulo de modelo de atleta.
Implementación según specs.md sección 2.1.
"""

import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from pydantic import validator
import reflex as rx
from sqlmodel import Field, Relationship

if TYPE_CHECKING:
    from .team_model import TeamMember
    from .tournament_model import Match


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
    age: int = Field(default=0)
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
    is_disqualified: bool = Field(default=False)

    # Timestamps
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.datetime.utcnow},
    )

    # Relaciones
    team_memberships: List["TeamMember"] = Relationship(back_populates="athlete")
    matches_as_aka: List["Match"] = Relationship(
        back_populates="aka",
        sa_relationship_kwargs={
            "foreign_keys": "Match.aka_id",
            "primaryjoin": "Athlete.id == Match.aka_id",
        },
    )
    matches_as_ao: List["Match"] = Relationship(
        back_populates="ao",
        sa_relationship_kwargs={
            "foreign_keys": "Match.ao_id",
            "primaryjoin": "Athlete.id == Match.ao_id",
        },
    )
    matches_won: List["Match"] = Relationship(
        back_populates="winner",
        sa_relationship_kwargs={
            "foreign_keys": "Match.winner_id",
            "primaryjoin": "Athlete.id == Match.winner_id",
        },
    )

    @validator("age")
    def age_non_negative(cls, v):
        if v < 0:
            raise ValueError("age cannot be negative")
        return v

    @validator("weight_kg")
    def weight_kg_valid_range(cls, v):
        if v is not None and (v < 40.0 or v > 120.0):
            raise ValueError("weight_kg must be between 40.0 and 120.0 kg")
        return v
