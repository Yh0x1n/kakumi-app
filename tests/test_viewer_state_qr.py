"""Tests for ViewerState QR integration — RED phase.

Tests verify that:
- ?code= query param is extracted from router params in load_viewer_dashboard
- load_viewer_dashboard works with valid/invalid codes
- B5 fix (double @rx.event) stays removed

Task 3.3 — Write tests for viewer_state QR integration (RED first)
"""

import datetime
import inspect

import pytest
import reflex as rx

from kakumi_app.models.tournament_model import Tournament, TournamentStatus
from kakumi_app.states.viewer_state import ViewerState


class MockPage:
    """Minimal mock for router.page with a params dict."""

    def __init__(self, params: dict[str, str]) -> None:
        self.params = params


class MockRouter:
    """Minimal mock for state.router with page.params."""

    def __init__(self, params: dict[str, str]) -> None:
        self.page = MockPage(params)


def _set_router(state: ViewerState, params: dict[str, str]) -> None:
    """Bypass Reflex __setattr__ to inject mock router onto state."""
    object.__setattr__(state, "router", MockRouter(params))


class TestViewerStateCodeParam:
    """Tests for ?code= query param extraction."""

    @pytest.mark.asyncio
    async def test_load_dashboard_extracts_code_param(self) -> None:
        """Router params with code -> viewer_code set to code value.

        RED: fails because load_viewer_dashboard doesn't extract ?code= yet.
        """
        state = ViewerState()  # type: ignore[call-arg]
        _set_router(state, {"code": "test1234"})

        await state.load_viewer_dashboard()

        assert state.viewer_code == "test1234"

    @pytest.mark.asyncio
    async def test_load_dashboard_no_code_param(self) -> None:
        """Empty router params -> viewer_code stays empty string."""
        state = ViewerState()  # type: ignore[call-arg]
        _set_router(state, {})

        await state.load_viewer_dashboard()

        assert state.viewer_code == ""

    @pytest.mark.asyncio
    async def test_load_dashboard_valid_code(
        self,
        db_session,
        sample_user,
    ) -> None:
        """Valid code + matching tournament ID -> dashboard loads.

        RED: fails because ?code= extraction missing, so viewer_code
        won't match the tournament's stored code.
        """
        with rx.session() as session:
            tournament = Tournament(
                name="Viewer QR Valid",
                venue="Dojo",
                start_date=datetime.date(2026, 6, 1),
                end_date=datetime.date(2026, 6, 3),
                tatami_count=1,
                status=TournamentStatus.PLANIFICADO.value,
                is_public=True,
                viewer_code="a1b2c3d4",
                viewer_code_generated_at=datetime.datetime.utcnow(),
                created_by_id=sample_user.id,
            )
            session.add(tournament)
            session.commit()
            session.refresh(tournament)
            tournament_id = tournament.id

        state = ViewerState()  # type: ignore[call-arg]
        _set_router(state, {"code": "a1b2c3d4", "tournament_id": str(tournament_id)})

        await state.load_viewer_dashboard()

        assert state.viewer_code == "a1b2c3d4"
        assert state.current_tournament is not None
        assert state.current_tournament["id"] == tournament_id
        assert not state.access_denied

    @pytest.mark.asyncio
    async def test_load_dashboard_invalid_code(
        self,
        db_session,
        sample_user,
    ) -> None:
        """Invalid code -> access_denied, no tournament loaded."""
        with rx.session() as session:
            tournament = Tournament(
                name="Viewer QR Invalid",
                venue="Dojo",
                start_date=datetime.date(2026, 6, 1),
                end_date=datetime.date(2026, 6, 3),
                tatami_count=1,
                status=TournamentStatus.PLANIFICADO.value,
                is_public=True,
                viewer_code="validcode",
                viewer_code_generated_at=datetime.datetime.utcnow(),
                created_by_id=sample_user.id,
            )
            session.add(tournament)
            session.commit()
            session.refresh(tournament)
            tournament_id = tournament.id

        state = ViewerState()  # type: ignore[call-arg]
        _set_router(state, {"code": "wrongcode", "tournament_id": str(tournament_id)})

        await state.load_viewer_dashboard()

        assert state.access_denied
        assert state.current_tournament is None

    def test_double_event_decorator_removed(self) -> None:
        """load_viewer_dashboard has exactly one @rx.event decorator.

        Regression guard for B5 fix (Task 1.3).
        """
        # inspect.getsource fails on EventHandler wrapper, use class source
        source = inspect.getsource(ViewerState)
        # Find lines around the load_viewer_dashboard method
        lines = source.splitlines()
        target_idx = None
        for i, line in enumerate(lines):
            if "def load_viewer_dashboard" in line:
                target_idx = i
                break
        assert target_idx is not None, "load_viewer_dashboard not found in class"

        # Count @rx.event in the 5 lines preceding the def
        preceding = lines[max(0, target_idx - 5) : target_idx]
        count = sum(1 for line in preceding if line.strip().startswith("@rx.event"))
        assert count == 1, f"Expected 1 @rx.event decorator, found {count}"
