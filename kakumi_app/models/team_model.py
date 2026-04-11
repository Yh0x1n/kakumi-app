"""
KAKUMI
Módulo de modelos de equipo y miembros de equipo.
Implementación según specs.md sección 2.2.
"""

import datetime
from typing import TYPE_CHECKING, List, Optional

import reflex as rx
from sqlmodel import Field, Relationship

if TYPE_CHECKING:
    from .athlete_model import Athlete
    from .tournament_model import TournamentCategory


class Team(rx.Model, table=True):
    """
    Modelo de Equipo para competiciones de Kata/Kumite por equipos.

    Un equipo debe tener entre 3 y 8 miembros para competir.
    Un atleta solo puede pertenecer a un equipo por categoría.
    """

    __tablename__ = "teams"

    # Campos obligatorios
    name: str = Field(max_length=255, index=True)
    category_id: int = Field(foreign_key="tournament_categories.id", index=True)
    member_count: int = Field(default=0)  # 3-8 para competencia
    is_active: bool = Field(default=True)

    # Campos opcionales
    dojo: Optional[str] = Field(default=None, max_length=255)

    # Timestamp
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    # Relaciones
    category: "TournamentCategory" = Relationship(
        back_populates="teams",
        sa_relationship_kwargs={"foreign_keys": "[Team.category_id]"},
    )
    members: List["TeamMember"] = Relationship(
        back_populates="team",
        sa_relationship_kwargs={"foreign_keys": "[TeamMember.team_id]"},
    )


class TeamMember(rx.Model, table=True):
    """
    Tabla de intersección entre Team y Athlete.

    Define la composición de un equipo: quiénes son titulares
    y quiénes son reservas, y en qué orden participan.
    """

    __tablename__ = "team_members"

    # Foreign Keys
    team_id: int = Field(foreign_key="teams.id", index=True)
    athlete_id: int = Field(foreign_key="athletes.id", index=True)

    # Datos de membresía
    position: int = Field(default=1)  # Orden de participación (1-8)
    is_reserve: bool = Field(default=False)  # True = reserva, False = titular

    # Timestamp
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    # Relaciones
    team: "Team" = Relationship(
        back_populates="members",
        sa_relationship_kwargs={"foreign_keys": "[TeamMember.team_id]"},
    )
    athlete: "Athlete" = Relationship(
        back_populates="team_memberships",
        sa_relationship_kwargs={"foreign_keys": "[TeamMember.athlete_id]"},
    )
