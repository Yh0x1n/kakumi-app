"""
KAKUMI
Módulo de modelo de árbitros
"""

from typing import Optional

import reflex as rx
from sqlmodel import Field


class Referee(rx.Model, table=True):
    """Tabla de los árbitros"""

    name: str = Field(unique=True, index=True)
    license: Optional[str] = Field(default=None)
    role: Optional[str] = Field(default=None)
