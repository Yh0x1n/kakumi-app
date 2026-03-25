"""
KAKUMI
Módulo de modelo de atleta
"""

from typing import TYPE_CHECKING, Optional

import reflex as rx
from sqlmodel import Field, Relationship

if TYPE_CHECKING:
    from .tournament_model import KataCategory, KumiteCategory


class Athlete(rx.Model, table=True):
    name: str = Field(unique=True, index=True)
    age: Optional[int] = None
    belt: Optional[str] = None
    weight_kg: Optional[float] = None

    kata_category_id: Optional[int] = Field(default=None, foreign_key="katacategory.id")
    kumite_category_id: Optional[int] = Field(
        default=None, foreign_key="kumitecategory.id"
    )

    # Relaciones
    kata_category: Optional["KataCategory"] = Relationship(back_populates="athletes")
    kumite_category: Optional["KumiteCategory"] = Relationship(
        back_populates="athletes"
    )
