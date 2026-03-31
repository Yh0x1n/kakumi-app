"""
KAKUMI
Módulo de modelo de equipo y miembros de equipo
"""

import datetime
from typing import TYPE_CHECKING, List, Optional

import reflex as rx
from sqlmodel import Field, Relationship, func
from pydantic import validator

if TYPE_CHECKING:
    from .tournament_model import KataCategory
    from .athlete_model import Athlete


class Team(rx.Model, table=True):
    name: str = Field(unique=True, index=True)
    dojo: Optional[str] = Field(default=None, max_length=255)
    category_id: int = Field(foreign_key="katacategory.id")
    member_count: int = Field(default=0)  # Se actualizará automáticamente
    is_active: bool = Field(default=True)
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        sa_column_kwargs={"server_default": func.now()},
    )

    # Relaciones
    category: "KataCategory" = Relationship(back_populates="teams")
    members: List["TeamMember"] = Relationship(back_populates="team")

    @validator("member_count")
    def member_count_valid_range(cls, v):
        if v < 0 or v > 8:
            raise ValueError("member_count must be between 0 and 8")
        return v


class TeamMember(rx.Model, table=True):
    """Tabla de intersección entre Team y Athlete"""

    team_id: int = Field(foreign_key="team.id")
    athlete_id: int = Field(foreign_key="athlete.id")
    position: int = Field(ge=1, le=8)
    is_reserve: bool = Field(default=False)

    # Relaciones
    team: "Team" = Relationship(back_populates="members")
    athlete: "Athlete" = Relationship(back_populates="team_members")

    # Restricción: un atleta solo puede pertenecer a un equipo por categoría
    # Esto se validará a nivel de servicio, no de base de datos.
