"""Persistence model for secondary public scoring display snapshots."""

from __future__ import annotations

import datetime
from typing import Optional

from reflex import Model
from sqlmodel import Field


class DisplaySession(Model, table=True):
    """Represents one public-display session and latest published snapshot."""

    __tablename__ = "display_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    display_key: str = Field(index=True, unique=True, max_length=64)
    modality: str = Field(max_length=16, index=True)
    source_kind: str = Field(max_length=16, index=True)
    match_id: Optional[int] = Field(default=None, foreign_key="matches.id", index=True)
    snapshot_json: str = Field(default="{}")
    is_active: bool = Field(default=True)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        index=True,
        sa_column_kwargs={"onupdate": datetime.datetime.utcnow},
    )
