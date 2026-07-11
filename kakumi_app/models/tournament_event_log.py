"""
KAKUMI - Tournament Event Log Model
=====================================
Modelo de auditoría para registrar cambios de estado de torneos.
Persiste el historial de transiciones según WKF compliance requirements.
"""

import datetime
from typing import Any, Optional

import reflex as rx
import sqlalchemy as sa
from sqlmodel import Field


class TournamentEventLog(rx.Model, table=True):
    """
    Audit log de cambios de estado en torneos.

    Registra cada transición de estado con contexto de usuario,
    timestamps y detalles opcionales para cumplimiento WKF.
    Los registros se mantienen indefinidamente (no hay TTL).
    """

    __tablename__ = "tournament_event_logs"

    # Foreign Keys
    tournament_id: int = Field(foreign_key="tournaments.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")

    # Tipo de evento (ej: "STATUS_CHANGE", "TRANSITION_ATTEMPT")
    event_type: str = Field(max_length=50)

    # Estados anterior y nuevo (almacenados como string para flexibilidad)
    old_status: Optional[str] = Field(default=None, max_length=50)
    new_status: Optional[str] = Field(default=None, max_length=50)

    # Detalles adicionales del evento (mensaje, razón, etc.)
    details: Optional[Any] = Field(
        default=None,
        sa_column=sa.Column(sa.JSON, nullable=True),
    )

    # Timestamp automático de cuando ocurrió el evento
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
