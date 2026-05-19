"""Tests for secondary display snapshot persistence service."""

from __future__ import annotations

import datetime
import json

import reflex as rx

from kakumi_app.models.display_model import DisplaySession
from kakumi_app.services.secondary_display_service import SecondaryDisplayService


def test_ensure_display_session_creates_new_key_and_row(sample_match) -> None:
    session = SecondaryDisplayService.ensure_display_session(
        modality="KUMITE",
        source_kind="TOURNAMENT",
        match_id=sample_match.id,
    )

    with rx.session() as db:
        stored = db.get(DisplaySession, session.id)

    assert session.display_key != ""
    assert stored is not None
    assert stored.modality == "KUMITE"
    assert stored.source_kind == "TOURNAMENT"
    assert stored.match_id == sample_match.id


def test_publish_snapshot_updates_payload_and_updated_at(sample_match) -> None:
    display_session = SecondaryDisplayService.ensure_display_session(
        modality="KATA",
        source_kind="TOURNAMENT",
        match_id=sample_match.id,
    )
    first_updated_at = display_session.updated_at

    payload = {
        "modality": "KATA",
        "title": "Kata en vivo",
        "aka": {"name": "AKA", "total": "25.10"},
    }
    updated = SecondaryDisplayService.publish_snapshot(
        display_key=display_session.display_key,
        snapshot=payload,
    )

    assert updated is not None
    with rx.session() as db:
        stored = db.get(DisplaySession, display_session.id)

    assert stored is not None
    assert json.loads(stored.snapshot_json) == payload
    assert stored.updated_at >= first_updated_at


def test_read_snapshot_returns_missing_for_unknown_key() -> None:
    result = SecondaryDisplayService.read_snapshot(
        display_key="does-not-exist",
        stale_after_seconds=5,
    )

    assert result.status == "missing"
    assert result.snapshot is None


def test_read_snapshot_returns_stale_when_updated_at_is_old(sample_match) -> None:
    display_session = SecondaryDisplayService.ensure_display_session(
        modality="KUMITE",
        source_kind="TOURNAMENT",
        match_id=sample_match.id,
    )
    SecondaryDisplayService.publish_snapshot(
        display_key=display_session.display_key,
        snapshot={"modality": "KUMITE", "timer_seconds": 91},
    )

    with rx.session() as db:
        stored = db.get(DisplaySession, display_session.id)
        assert stored is not None
        stored.updated_at = datetime.datetime.utcnow() - datetime.timedelta(seconds=90)
        db.add(stored)
        db.commit()

    result = SecondaryDisplayService.read_snapshot(
        display_key=display_session.display_key,
        stale_after_seconds=5,
    )

    assert result.status == "stale"
    assert result.snapshot is not None


def test_read_snapshot_returns_ok_with_payload(sample_match) -> None:
    display_session = SecondaryDisplayService.ensure_display_session(
        modality="KUMITE",
        source_kind="TOURNAMENT",
        match_id=sample_match.id,
    )
    payload = {
        "modality": "KUMITE",
        "timer_seconds": 120,
        "aka": {"name": "AKA", "score": 3},
        "ao": {"name": "AO", "score": 1},
    }
    SecondaryDisplayService.publish_snapshot(
        display_key=display_session.display_key,
        snapshot=payload,
    )

    result = SecondaryDisplayService.read_snapshot(
        display_key=display_session.display_key,
        stale_after_seconds=120,
    )

    assert result.status == "ok"
    assert result.snapshot == payload
