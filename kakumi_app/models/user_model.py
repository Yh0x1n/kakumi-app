"""
KAKUMI
Módulo de modelo de usuario.
Implementación según specs.md sección 2.9.
"""

import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

import reflex as rx
from sqlmodel import Field, Relationship

if TYPE_CHECKING:
    from .tournament_model import MatchScore, Tournament


class UserRole(str, Enum):
    """Roles de usuario en el sistema."""

    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


class User(rx.Model, table=True):
    """
    Usuario del sistema para autenticación y autorización.

    Roles:
    - ADMIN: Administrador del sistema (acceso total)
    - OPERATOR: Operador de torneo (gestión operativa)
    - VIEWER: Espectador (solo lectura)
    """

    __tablename__ = "users"

    # Campos obligatorios
    username: str = Field(unique=True, index=True, max_length=50)
    email: str = Field(unique=True, index=True, max_length=255)
    password_hash: str = Field(max_length=255)
    full_name: str = Field(max_length=255)
    role: str = Field(default=UserRole.OPERATOR.value)

    # Campos opcionales
    is_active: bool = Field(default=True)
    last_login: Optional[datetime.datetime] = Field(default=None)

    # Campos de tracking de seguridad
    failed_attempts: int = Field(default=0)
    locked_until: Optional[datetime.datetime] = Field(default=None)
    last_activity: Optional[datetime.datetime] = Field(default=None)

    # Timestamp
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    # Relaciones
    created_tournaments: List["Tournament"] = Relationship(
        back_populates="created_by",
        sa_relationship_kwargs={"foreign_keys": "[Tournament.created_by_id]"},
    )
    applied_scores: List["MatchScore"] = Relationship(
        back_populates="applied_by",
        sa_relationship_kwargs={"foreign_keys": "[MatchScore.applied_by_id]"},
    )
