"""Tests for TournamentState QR event handlers.

RED phase: Tests fail because QR state vars/handlers don't exist yet.
GREEN: All pass after Task 2.4 implementation.
"""

import datetime

import pytest
import reflex as rx

from kakumi_app.models.tournament_model import Tournament, TournamentStatus
from kakumi_app.states.tournament_state import TournamentState


async def _drain(gen):
    """Drain an async generator, collecting yielded events."""
    return [event async for event in gen]


class TestTournamentStateQR:
    """Tests for QR generation/regeneration in TournamentState."""

    def test_generate_qr_default_state(self, db_session):
        """Initial state: all QR vars are empty strings."""
        state = TournamentState()  # type: ignore[call-arg]
        assert state.qr_data_url == ""
        assert state.qr_code_text == ""
        assert state.qr_generated_at == ""
        assert state.qr_expires_at == ""

    @pytest.mark.asyncio
    async def test_generate_qr_no_tournament(self, db_session):
        """No current_tournament -> error toast, vars stay empty."""
        state = TournamentState()  # type: ignore[call-arg]
        state.current_tournament = None

        events = await _drain(state.generate_qr())

        # Should have yielded at least one event (toast)
        assert len(events) > 0
        # Vars should still be empty
        assert state.qr_data_url == ""
        assert state.qr_code_text == ""

    @pytest.mark.asyncio
    async def test_generate_qr_success(self, db_session, sample_user):  # noqa: F811
        """Tournament selected -> QR vars populated, data URI valid."""
        # Create a tournament in DB
        with rx.session() as session:
            tournament = Tournament(
                name="QR Test Tournament",
                venue="Test Dojo",
                start_date=datetime.date(2026, 7, 1),
                end_date=datetime.date(2026, 7, 3),
                tatami_count=2,
                status=TournamentStatus.PLANIFICADO.value,
                is_public=True,
                created_by_id=sample_user.id,
            )
            session.add(tournament)
            session.commit()
            session.refresh(tournament)
            tournament_id = tournament.id

        state = TournamentState()  # type: ignore[call-arg]
        state.current_tournament = {"id": tournament_id, "name": "QR Test Tournament"}
        state._current_user_id = sample_user.id

        events = await _drain(state.generate_qr())

        assert len(events) > 0
        assert state.qr_data_url != ""
        assert state.qr_data_url.startswith("data:image/png;base64,")
        assert len(state.qr_code_text) == 8
        assert state.qr_generated_at != ""
        assert state.qr_expires_at != ""

    @pytest.mark.asyncio
    async def test_generate_qr_expiry_correct(
        self,
        db_session,
        sample_user,  # noqa: F811
    ):
        """qr_expires_at is 5h after qr_generated_at."""
        with rx.session() as session:
            tournament = Tournament(
                name="Expiry Test Tournament",
                venue="Test Dojo",
                start_date=datetime.date(2026, 7, 1),
                end_date=datetime.date(2026, 7, 3),
                tatami_count=2,
                status=TournamentStatus.PLANIFICADO.value,
                is_public=True,
                created_by_id=sample_user.id,
            )
            session.add(tournament)
            session.commit()
            session.refresh(tournament)
            tournament_id = tournament.id

        state = TournamentState()  # type: ignore[call-arg]
        state.current_tournament = {"id": tournament_id, "name": "Expiry Test"}
        state._current_user_id = sample_user.id

        await _drain(state.generate_qr())

        # Parse timestamps
        generated = datetime.datetime.strptime(
            state.qr_generated_at, "%Y-%m-%d %H:%M UTC"
        )
        expires = datetime.datetime.strptime(state.qr_expires_at, "%Y-%m-%d %H:%M UTC")
        diff = expires - generated
        assert diff == datetime.timedelta(hours=5), f"Expected 5h, got {diff}"

    @pytest.mark.asyncio
    async def test_regenerate_qr_new_code(self, db_session, sample_user):  # noqa: F811
        """Regenerate produces a different code than the first one."""
        with rx.session() as session:
            tournament = Tournament(
                name="Regen Test Tournament",
                venue="Test Dojo",
                start_date=datetime.date(2026, 7, 1),
                end_date=datetime.date(2026, 7, 3),
                tatami_count=2,
                status=TournamentStatus.PLANIFICADO.value,
                is_public=True,
                created_by_id=sample_user.id,
            )
            session.add(tournament)
            session.commit()
            session.refresh(tournament)
            tournament_id = tournament.id

        state = TournamentState()  # type: ignore[call-arg]
        state.current_tournament = {"id": tournament_id, "name": "Regen Test"}
        state._current_user_id = sample_user.id

        # First generation
        await _drain(state.generate_qr())
        first_code = state.qr_code_text
        first_url = state.qr_data_url

        # Regenerate
        await _drain(state.regenerate_qr())
        second_code = state.qr_code_text
        second_url = state.qr_data_url

        assert second_code != first_code, "New code should differ from old"
        assert second_url != first_url, "New QR should differ from old"

    @pytest.mark.asyncio
    async def test_regenerate_qr_old_code_invalid(
        self,
        db_session,
        sample_user,  # noqa: F811
    ):
        """Old code no longer validates after regenerate."""
        from kakumi_app.services.viewer_service import ViewerService

        with rx.session() as session:
            tournament = Tournament(
                name="Invalidate Test Tournament",
                venue="Test Dojo",
                start_date=datetime.date(2026, 7, 1),
                end_date=datetime.date(2026, 7, 3),
                tatami_count=2,
                status=TournamentStatus.PLANIFICADO.value,
                is_public=True,
                created_by_id=sample_user.id,
            )
            session.add(tournament)
            session.commit()
            session.refresh(tournament)
            tournament_id = tournament.id

        state = TournamentState()  # type: ignore[call-arg]
        state.current_tournament = {"id": tournament_id, "name": "Invalidate Test"}
        state._current_user_id = sample_user.id

        # First generation
        await _drain(state.generate_qr())
        old_code = state.qr_code_text

        # After regenerate, old code should fail validation
        await _drain(state.regenerate_qr())

        # Old code should not validate anymore
        result = ViewerService.validate_viewer_code(old_code)
        assert result is None, "Old code should be invalid after regenerate"
