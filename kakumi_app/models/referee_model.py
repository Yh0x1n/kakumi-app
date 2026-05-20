"""
KAKUMI
Módulo de modelo de árbitros.
Implementación según specs.md sección 2.7.
"""

import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

import reflex as rx
from sqlmodel import Field, Relationship

if TYPE_CHECKING:
    from .tournament_model import Match, MatchScore, Penalty


class LicenseLevel(str, Enum):
    """Nivel de licencia de arbitraje según WKF."""

    NATIONAL = "NATIONAL"
    INTERNATIONAL = "INTERNATIONAL"


class RefereeRole(str, Enum):
    """Roles de árbitros en competición."""

    REFEREE = "REFEREE"
    JUDGE = "JUDGE"
    TABLE_OFFICIAL = "TABLE_OFFICIAL"
    SUPERVISOR = "SUPERVISOR"


class Referee(rx.Model, table=True):
    """
    Modelo de Árbitro / Juez / Oficial de mesa.

    Roles:
    - REFEREE (RF): Árbitro principal, inicia/detiene combate
    - JUDGE (JD): Juez de kata o kumite, otorga puntuaciones
    - TABLE_OFFICIAL (TO): Oficial de mesa, gestiona datos
    - SUPERVISOR (SP): Supervisor general del tatami
    """

    __tablename__ = "referees"

    # Campos obligatorios
    name: str = Field(max_length=255, index=True)
    license_number: str = Field(max_length=50, index=True)
    license_level: str = Field(default=LicenseLevel.NATIONAL.value)
    role: str = Field(default=RefereeRole.REFEREE.value)
    is_available: bool = Field(default=True)

    # Campos opcionales
    tatami_certified: Optional[str] = Field(
        default=None
    )  # JSON array de tatamis certificados
    dojo: Optional[str] = Field(default=None, max_length=255)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)

    # Timestamps
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.datetime.utcnow},
    )

    # Relaciones (back_populates desde tournament_model)
    matches_as_referee: List["Match"] = Relationship(
        back_populates="referee",
        sa_relationship_kwargs={"foreign_keys": "[Match.referee_id]"},
    )
    scores_as_judge: List["MatchScore"] = Relationship(
        back_populates="judge",
        sa_relationship_kwargs={"foreign_keys": "[MatchScore.judge_id]"},
    )
    penalties_given: List["Penalty"] = Relationship(
        back_populates="given_by",
        sa_relationship_kwargs={"foreign_keys": "[Penalty.given_by_id]"},
    )
