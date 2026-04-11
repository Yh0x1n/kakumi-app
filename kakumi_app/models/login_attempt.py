"""
Login Attempt Tracking Model
===========================
Tracks all login attempts for audit and security analysis purposes.
"""

from typing import Optional
from datetime import datetime
from reflex import Model
from sqlmodel import Field


class LoginAttempt(Model, table=True):
    __tablename__ = "login_attempts"

    id: int = Field(primary_key=True)
    username: str = Field(max_length=50, index=True)
    ip_address: Optional[str] = Field(max_length=45)
    user_agent: Optional[str] = Field(max_length=255)
    was_successful: bool = Field(default=False)
    failure_reason: Optional[str] = Field(max_length=50)
    created_at: datetime = Field(default_factory=datetime.utcnow)
