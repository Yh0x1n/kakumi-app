"""Service to manage shared secondary-display snapshot state."""

from __future__ import annotations

import datetime
import json
import secrets
from dataclasses import dataclass
from typing import Any

import reflex as rx
from sqlmodel import select

from kakumi_app.models.display_model import DisplaySession


@dataclass
class SecondaryDisplayReadResult:
    """Read contract for public display polling."""

    status: str
    snapshot: dict[str, Any] | None
    updated_at: datetime.datetime | None


class SecondaryDisplayService:
    """Persistence-backed synchronization for operator/public display sessions."""

    @staticmethod
    def _generate_display_key() -> str:
        return secrets.token_urlsafe(16)

    @staticmethod
    def ensure_display_session(
        *,
        modality: str,
        source_kind: str,
        match_id: int | None,
    ) -> DisplaySession:
        """Create or return an active session for (modality, source, match)."""
        with rx.session() as session:
            statement = select(DisplaySession).where(
                DisplaySession.modality == modality,
                DisplaySession.source_kind == source_kind,
                DisplaySession.match_id == match_id,
                DisplaySession.is_active.is_(True),
            )
            existing = session.exec(statement).first()
            if existing is not None:
                return existing

            display_session = DisplaySession(
                display_key=SecondaryDisplayService._generate_display_key(),
                modality=modality,
                source_kind=source_kind,
                match_id=match_id,
                snapshot_json="{}",
                is_active=True,
            )
            session.add(display_session)
            session.commit()
            session.refresh(display_session)
            return display_session

    @staticmethod
    def publish_snapshot(
        *,
        display_key: str,
        snapshot: dict[str, Any],
    ) -> DisplaySession | None:
        """Persist latest normalized snapshot for one display key."""
        with rx.session() as session:
            display_session = session.exec(
                select(DisplaySession).where(DisplaySession.display_key == display_key)
            ).first()
            if display_session is None:
                return None
            display_session.snapshot_json = json.dumps(snapshot)
            display_session.updated_at = datetime.datetime.utcnow()
            session.add(display_session)
            session.commit()
            session.refresh(display_session)
            return display_session

    @staticmethod
    def read_snapshot(
        *,
        display_key: str,
        stale_after_seconds: int,
    ) -> SecondaryDisplayReadResult:
        """Read latest snapshot and compute missing/stale/ok status."""
        with rx.session() as session:
            display_session = session.exec(
                select(DisplaySession).where(DisplaySession.display_key == display_key)
            ).first()
            if display_session is None:
                return SecondaryDisplayReadResult(
                    status="missing",
                    snapshot=None,
                    updated_at=None,
                )

            snapshot = json.loads(display_session.snapshot_json or "{}")
            age = datetime.datetime.utcnow() - display_session.updated_at
            status = "stale" if age.total_seconds() > stale_after_seconds else "ok"
            return SecondaryDisplayReadResult(
                status=status,
                snapshot=snapshot,
                updated_at=display_session.updated_at,
            )
