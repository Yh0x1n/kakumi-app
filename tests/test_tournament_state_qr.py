"""Tests for TournamentState QR event handlers.

RED phase: Tests fail because QR state vars/handlers don't exist yet.
GREEN: All pass after Task 2.4 implementation.
"""

import datetime
from unittest.mock import MagicMock

import pytest
import reflex as rx

from kakumi_app.models.tournament_model import Tournament, TournamentStatus
from kakumi_app.states.tournament_state import TournamentState


async def _drain(gen):
    """Drain an async generator, collecting yielded events."""
    return [event async for event in gen]


# ── Tests for _resolve_base_url() — Task 3.1 ──


class TestResolveBaseUrl:
    """Tests for TournamentState._resolve_base_url() pure function."""

    def test_origin_available_returns_origin(self):
        """router.url.origin present -> return as-is."""
        router = MagicMock()
        router.url = MagicMock()
        router.url.origin = "https://example.com"

        result = TournamentState._resolve_base_url(router)

        assert result == "https://example.com"

    def test_fallback_host_header(self):
        """No origin -> use Host header with http://."""
        router = MagicMock()
        router.url = ""  # string, no origin attr
        router.headers = {"host": "kakumi.app"}

        result = TournamentState._resolve_base_url(router)

        assert result == "http://kakumi.app"

    def test_forwarded_proto_https(self):
        """X-Forwarded-Proto: https -> https scheme."""
        router = MagicMock()
        router.url = ""
        router.headers = MagicMock()
        router.headers.get.side_effect = lambda k, d=None: (
            "kakumi.app" if k == "host" else d
        )
        router.headers.raw_headers = {b"x-forwarded-proto": [b"https"]}

        result = TournamentState._resolve_base_url(router)

        assert result == "https://kakumi.app"

    def test_forwarded_proto_and_host(self):
        """X-Forwarded-Proto + X-Forwarded-Host combined."""
        router = MagicMock()
        router.url = ""
        router.headers = MagicMock()
        router.headers.get.side_effect = lambda k, d=None: (
            "localhost:3000" if k == "host" else d
        )
        router.headers.raw_headers = {
            b"x-forwarded-proto": [b"https"],
            b"x-forwarded-host": [b"cdn.kakumi.app"],
        }

        result = TournamentState._resolve_base_url(router)

        assert result == "https://cdn.kakumi.app"

    def test_forwarded_proto_no_forwarded_host(self):
        """X-Forwarded-Proto only -> use Host for hostname."""
        router = MagicMock()
        router.url = ""
        router.headers = MagicMock()
        router.headers.get.side_effect = lambda k, d=None: (
            "kakumi.app" if k == "host" else d
        )
        router.headers.raw_headers = {b"x-forwarded-proto": [b"https"]}

        result = TournamentState._resolve_base_url(router)

        assert result == "https://kakumi.app"

    def test_no_origin_no_headers(self):
        """Nothing available -> http://localhost:3000 default."""
        router = MagicMock()
        router.url = ""
        router.headers = {"host": "localhost:3000"}

        result = TournamentState._resolve_base_url(router)

        assert result == "http://localhost:3000"


# ── Tests for QR state clearing — Task 3.2 ───


class TestQRStateClearing:
    """QR state vars cleared when tournament changes."""

    @pytest.mark.asyncio
    async def test_qr_vars_cleared_after_set_current_tournament(
        self,
        db_session,
        sample_user,
    ):
        """Switching tournaments clears QR state vars."""
        # Create two tournaments
        with rx.session() as session:
            t1 = Tournament(
                name="QR Clear Test A",
                venue="Dojo A",
                start_date=datetime.date(2026, 8, 1),
                end_date=datetime.date(2026, 8, 3),
                tatami_count=2,
                status=TournamentStatus.PLANIFICADO.value,
                is_public=True,
                created_by_id=sample_user.id,
            )
            t2 = Tournament(
                name="QR Clear Test B",
                venue="Dojo B",
                start_date=datetime.date(2026, 9, 1),
                end_date=datetime.date(2026, 9, 3),
                tatami_count=2,
                status=TournamentStatus.PLANIFICADO.value,
                is_public=True,
                created_by_id=sample_user.id,
            )
            session.add(t1)
            session.add(t2)
            session.commit()
            session.refresh(t1)
            session.refresh(t2)
            t1_id = t1.id
            t2_id = t2.id

        state = TournamentState()  # type: ignore[call-arg]
        state._current_user_id = sample_user.id
        state.current_tournament = {"id": t1_id, "name": "QR Clear Test A"}
        # Simulate QR vars populated
        state.qr_data_url = "data:image/png;base64,abc"
        state.qr_code_text = "a1b2c3d4"
        state.qr_generated_at = "2026-08-01 10:00 UTC"
        state.qr_expires_at = "2026-08-01 15:00 UTC"
        state.qr_viewer_url = "https://example.com/viewer/dashboard/1?code=a1b2c3d4"

        # Select tournament B
        await state.set_current_tournament(t2_id)

        # QR vars should be cleared
        assert state.qr_data_url == "", f"Expected '', got '{state.qr_data_url}'"
        assert state.qr_code_text == "", f"Expected '', got '{state.qr_code_text}'"
        assert state.qr_generated_at == "", f"Expected '', got '{state.qr_generated_at}'"
        assert state.qr_expires_at == "", f"Expected '', got '{state.qr_expires_at}'"
        assert state.qr_viewer_url == "", f"Expected '', got '{state.qr_viewer_url}'"

# ── Tests for qr_viewer_url format — Task 3.3 ─


class TestQRViewerUrl:
    """Tests for qr_viewer_url populated by generate_qr()."""

    @pytest.mark.asyncio
    async def test_qr_viewer_url_format_after_generate(
        self,
        db_session,
        sample_user,
        monkeypatch,
    ):
        """generate_qr() sets qr_viewer_url to expected viewer URL."""
        with rx.session() as session:
            t = Tournament(
                name="Viewer URL Test",
                venue="Dojo",
                start_date=datetime.date(2026, 8, 1),
                end_date=datetime.date(2026, 8, 3),
                tatami_count=2,
                status=TournamentStatus.PLANIFICADO.value,
                is_public=True,
                created_by_id=sample_user.id,
            )
            session.add(t)
            session.commit()
            session.refresh(t)
            t_id = t.id

        state = TournamentState()  # type: ignore[call-arg]
        state.current_tournament = {"id": t_id, "name": "Viewer URL Test"}
        state._current_user_id = sample_user.id

        # Force _resolve_base_url to return known value via class-level patch
        monkeypatch.setattr(
            TournamentState,
            "_resolve_base_url",
            staticmethod(lambda router: "https://kakumi.app"),
        )

        await _drain(state.generate_qr())

        assert state.qr_viewer_url != ""
        assert state.qr_viewer_url.startswith("https://kakumi.app/viewer/dashboard/")
        assert f"?code={state.qr_code_text}" in state.qr_viewer_url

    @pytest.mark.asyncio
    async def test_qr_viewer_url_https_scheme(
        self,
        db_session,
        sample_user,
        monkeypatch,
    ):
        """Verify different base URL schemes produce correct viewer URLs."""
        with rx.session() as session:
            t = Tournament(
                name="Viewer Scheme Test",
                venue="Dojo",
                start_date=datetime.date(2026, 8, 1),
                end_date=datetime.date(2026, 8, 3),
                tatami_count=2,
                status=TournamentStatus.PLANIFICADO.value,
                is_public=True,
                created_by_id=sample_user.id,
            )
            session.add(t)
            session.commit()
            session.refresh(t)
            t_id = t.id

        state = TournamentState()  # type: ignore[call-arg]
        state.current_tournament = {"id": t_id, "name": "Viewer Scheme Test"}
        state._current_user_id = sample_user.id

        monkeypatch.setattr(
            TournamentState,
            "_resolve_base_url",
            staticmethod(lambda router: "http://localhost:3000"),
        )

        await _drain(state.generate_qr())

        assert state.qr_viewer_url.startswith("http://localhost:3000/viewer/dashboard/")


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
