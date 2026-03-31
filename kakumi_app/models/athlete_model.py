"""
KAKUMI
Módulo de modelo de atleta
"""

import datetime
from typing import TYPE_CHECKING, List, Optional

import reflex as rx
from sqlmodel import Field, Relationship, col, func
from pydantic import validator

if TYPE_CHECKING:
    from .tournament_model import KataCategory, KumiteCategory
    from .team_model import TeamMember
    from .referee_model import Referee


class Athlete(rx.Model, table=True):
    name: str = Field(unique=True, index=True)
    email: Optional[str] = Field(default=None, unique=True, index=True)
    date_of_birth: datetime.date
    gender: str  # MALE / FEMALE
    weight_kg: Optional[float] = None
    belt_rank: Optional[str] = Field(default=None, max_length=50)
    dojo: Optional[str] = Field(default=None, max_length=255)
    nationality: Optional[str] = Field(default=None, max_length=3)
    license_number: Optional[str] = Field(default=None, max_length=50)
    is_active: bool = Field(default=True)
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )

    kata_category_id: Optional[int] = Field(default=None, foreign_key="katacategory.id")
    kumite_category_id: Optional[int] = Field(
        default=None, foreign_key="kumitecategory.id"
    )
    referee_id: Optional[int] = Field(default=None, foreign_key="referee.id")

    # Relaciones
    kata_category: Optional["KataCategory"] = Relationship(back_populates="athletes")
    kumite_category: Optional["KumiteCategory"] = Relationship(
        back_populates="athletes"
    )
    team_members: List["TeamMember"] = Relationship(back_populates="athlete")
    referee: Optional["Referee"] = Relationship(back_populates="athlete")

    @validator("date_of_birth")
    def date_of_birth_not_future(cls, v):
        if v > datetime.date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return v

    @validator("weight_kg")
    def weight_kg_valid_range(cls, v):
        if v is not None and (v < 40.0 or v > 120.0):
            raise ValueError("weight_kg must be between 40.0 and 120.0 kg")
        return v
