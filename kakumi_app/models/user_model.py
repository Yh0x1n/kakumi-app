"""
KAKUMI
Módulo de modelo de usuario
"""

import datetime
from typing import Optional

import reflex as rx
from sqlmodel import Field, func


class User(rx.Model, table=True):
    username: str = Field(unique=True, index=True, max_length=50)
    email: str = Field(unique=True, index=True, max_length=255)
    password_hash: str = Field(max_length=255)
    full_name: str = Field(max_length=255)
    role: str  # ADMIN / OPERATOR / VIEWER
    is_active: bool = Field(default=True)
    last_login: Optional[datetime.datetime] = None
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        sa_column_kwargs={"server_default": func.now()},
    )
