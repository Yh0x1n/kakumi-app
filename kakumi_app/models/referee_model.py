"""
KAKUMI
Módulo de modelo de árbitros
"""

import datetime
from typing import TYPE_CHECKING, List, Optional

import reflex as rx
from sqlmodel import Field, Relationship, func

if TYPE_CHECKING:
    from .athlete_model import Athlete


class Referee(rx.Model, table=True):
    """Tabla de los árbitros"""

    name: str = Field(unique=True, index=True)
    license_number: str = Field(max_length=50)
    license_level: str  # NATIONAL / INTERNATIONAL
    role: str  # REFEREE / JUDGE / TABLE_OFFICIAL / SUPERVISOR
    tatami_certified: Optional[str] = Field(default=None)  # JSON string de array
    is_available: bool = Field(default=True)
    dojo: Optional[str] = Field(default=None, max_length=255)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        sa_column_kwargs={"server_default": func.now()},
    )

    # Relaciones
    athlete: Optional["Athlete"] = Relationship(back_populates="referee")
