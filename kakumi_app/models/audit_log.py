"""
Audit Log Model
===============
Logs authentication events for compliance and forensic analysis.
"""

from typing import Optional
from datetime import datetime
from reflex import Model
from sqlmodel import Field


class AuditLog(Model, table=True):
    __tablename__ = "audit_logs"

    id: int = Field(primary_key=True)
    event_type: str = Field(max_length=50, index=True)
    user_id: Optional[int] = Field(foreign_key="users.id", index=True)
    username: Optional[str] = Field(max_length=50)
    ip_address: Optional[str] = Field(max_length=45)
    user_agent: Optional[str] = Field(max_length=255)
    details: Optional[str] = Field(max_length=1000)  # JSON-compatible additional data
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
