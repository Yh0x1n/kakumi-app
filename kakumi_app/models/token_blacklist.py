"""
JWT Token Blacklist Model
=========================
Tracks invalidated JWT tokens for refresh rotation and logout enforcement.
"""

from typing import Optional
from datetime import datetime
from reflex import Model
from sqlmodel import Field


class TokenBlacklist(Model, table=True):
    __tablename__ = "token_blacklist"

    id: int = Field(primary_key=True)
    token_jti: str = Field(max_length=255, index=True, unique=True)
    user_id: int = Field(foreign_key="users.id")
    token_type: str = Field(max_length=20)  # "access" or "refresh"
    expires_at: datetime
    blacklisted_at: datetime = Field(default_factory=datetime.utcnow)
    reason: Optional[str] = Field(max_length=50)
