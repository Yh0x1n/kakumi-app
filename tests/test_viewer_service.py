"""
Tests for ViewerService — RED phase.
See tasks.md Task 1.5 for full test matrix.
"""

import datetime
import re

import pytest

from kakumi_app.models.tournament_model import Tournament, TournamentStatus
from kakumi_app.services.viewer_service import ViewerService


# =============================================================================
# IS CODE EXPIRED — Unit tests (no DB needed)
# =============================================================================


@pytest.fixture
def tournament_with_code() -> Tournament:
    """Create a Tournament with viewer_code and generated_at set."""
    t = Tournament(
        name="Test Viewer",
        venue="Dojo",
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 3),
        status=TournamentStatus.PLANIFICADO.value,
        tatami_count=1,
        is_public=True,
        viewer_code="a1b2c3d4",
    )
    return t


def test_is_code_expired_within_5h(tournament_with_code: Tournament) -> None:
    """Code 4.5h old → not expired (False)."""
    tournament_with_code.viewer_code_generated_at = (
        datetime.datetime.utcnow() - datetime.timedelta(hours=4, minutes=30)
    )
    assert ViewerService._is_code_expired(tournament_with_code) is False


def test_is_code_expired_exactly_at_5h(tournament_with_code: Tournament) -> None:
    """Code 5h+1s old → expired (True)."""
    tournament_with_code.viewer_code_generated_at = (
        datetime.datetime.utcnow() - datetime.timedelta(hours=5, seconds=1)
    )
    assert ViewerService._is_code_expired(tournament_with_code) is True


def test_is_code_expired_null(tournament_with_code: Tournament) -> None:
    """NULL timestamp → expired (True)."""
    tournament_with_code.viewer_code_generated_at = None
    assert ViewerService._is_code_expired(tournament_with_code) is True


def test_is_code_expired_fresh(tournament_with_code: Tournament) -> None:
    """Code 1min old → not expired (False)."""
    tournament_with_code.viewer_code_generated_at = (
        datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
    )
    assert ViewerService._is_code_expired(tournament_with_code) is False


# =============================================================================
# GENERATE VIEWER CODE — Integration tests (DB via db_session fixture)
# =============================================================================


def test_generate_viewer_code_success(db_session) -> None:
    """Valid tournament ID → returns 8-char hex, saves to DB."""
    tournament = Tournament(
        name="Gen Code Test",
        venue="Dojo",
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 3),
        status=TournamentStatus.PLANIFICADO.value,
        tatami_count=1,
        is_public=True,
    )
    db_session.add(tournament)
    db_session.commit()
    db_session.refresh(tournament)

    tid = tournament.id
    code = ViewerService.generate_viewer_code(tid)

    assert code is not None
    assert len(code) == 8
    assert re.fullmatch(r"[0-9a-f]{8}", code)

    # Verify saved in DB
    db_session.refresh(tournament)
    assert tournament.viewer_code == code
    assert tournament.viewer_code_generated_at is not None


def test_generate_viewer_code_not_found() -> None:
    """Bogus tournament ID → None."""
    code = ViewerService.generate_viewer_code(999999)
    assert code is None


def test_generate_viewer_code_format(db_session) -> None:
    """Generated code matches ^[0-9a-f]{8}$."""
    tournament = Tournament(
        name="Format Test",
        venue="Dojo",
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 3),
        status=TournamentStatus.PLANIFICADO.value,
        tatami_count=1,
        is_public=True,
    )
    db_session.add(tournament)
    db_session.commit()
    db_session.refresh(tournament)

    code = ViewerService.generate_viewer_code(tournament.id)
    assert code is not None
    assert re.fullmatch(r"[0-9a-f]{8}", code)


# =============================================================================
# VALIDATE VIEWER CODE — Integration + Unit tests
# =============================================================================


def test_validate_viewer_code_valid(db_session) -> None:
    """Valid code + within 5h → returns tournament."""
    now = datetime.datetime.utcnow()
    tournament = Tournament(
        name="Validate Valid",
        venue="Dojo",
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 3),
        status=TournamentStatus.PLANIFICADO.value,
        tatami_count=1,
        is_public=True,
        viewer_code="deadbeef",
        viewer_code_generated_at=now - datetime.timedelta(hours=1),
    )
    db_session.add(tournament)
    db_session.commit()

    result = ViewerService.validate_viewer_code("deadbeef")
    assert result is not None
    assert result.id == tournament.id


def test_validate_viewer_code_nonexistent() -> None:
    """Code not in DB → None."""
    result = ViewerService.validate_viewer_code("n0nex1st")
    assert result is None


def test_validate_viewer_code_expired(db_session) -> None:
    """Code 6h old → None."""
    now = datetime.datetime.utcnow()
    tournament = Tournament(
        name="Validate Expired",
        venue="Dojo",
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 3),
        status=TournamentStatus.PLANIFICADO.value,
        tatami_count=1,
        is_public=True,
        viewer_code="exp1red0",
        viewer_code_generated_at=now - datetime.timedelta(hours=6),
    )
    db_session.add(tournament)
    db_session.commit()

    result = ViewerService.validate_viewer_code("exp1red0")
    assert result is None


def test_validate_viewer_code_locked(tournament_with_code: Tournament) -> None:
    """5+ fails within 5min → None (locked)."""
    tournament_with_code.viewer_code = "l0cked00"
    tournament_with_code.viewer_code_generated_at = datetime.datetime.utcnow()

    # Simulate 5 failed attempts
    ViewerService._failed_attempts["l0cked00"] = (5, datetime.datetime.utcnow())

    result = ViewerService.validate_viewer_code("l0cked00")
    assert result is None

    # Cleanup
    ViewerService._reset_attempts("l0cked00")


# =============================================================================
# CHECK VIEWER ACCESS — Integration tests
# =============================================================================


def test_check_viewer_access_correct(db_session) -> None:
    """Valid code + matching tournament → True."""
    now = datetime.datetime.utcnow()
    tournament = Tournament(
        name="Access Correct",
        venue="Dojo",
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 3),
        status=TournamentStatus.PLANIFICADO.value,
        tatami_count=1,
        is_public=True,
        viewer_code="acc3ss00",
        viewer_code_generated_at=now - datetime.timedelta(hours=1),
    )
    db_session.add(tournament)
    db_session.commit()

    assert ViewerService.check_viewer_access("acc3ss00", tournament.id) is True


def test_check_viewer_access_wrong_tournament(db_session) -> None:
    """Valid code + wrong tournament ID → False."""
    now = datetime.datetime.utcnow()
    tournament = Tournament(
        name="Access Wrong",
        venue="Dojo",
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 3),
        status=TournamentStatus.PLANIFICADO.value,
        tatami_count=1,
        is_public=True,
        viewer_code="wr0ng00a",
        viewer_code_generated_at=now - datetime.timedelta(hours=1),
    )
    db_session.add(tournament)
    db_session.commit()

    # Use a non-existent tournament ID
    assert ViewerService.check_viewer_access("wr0ng00a", 999999) is False
