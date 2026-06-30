"""Tests for DashboardState (dashboard winner cards)."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import reflex as rx

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.tournament_model import (
    CategoryStatus,
    CompetitionSystem,
    Match,
    MatchStatus,
    MatchType,
    Modality,
    Tournament,
    TournamentCategory,
)


def _create_tournament(*, name: str) -> Tournament:
    with rx.session() as session:
        tournament = Tournament(
            name=name,
            venue="Dojo Dashboard",
            start_date=datetime.date(2026, 11, 1),
            end_date=datetime.date(2026, 11, 2),
            tatami_count=2,
            status="PLANIFICADO",
            is_public=True,
        )
        session.add(tournament)
        session.commit()
        session.refresh(tournament)
        return tournament


def _create_athlete(*, name: str) -> Athlete:
    with rx.session() as session:
        athlete = Athlete(
            name=name,
            age=25,
            gender="MALE",
            email=f"{name.lower().replace(' ', '.')}@dash.test",
        )
        session.add(athlete)
        session.commit()
        session.refresh(athlete)
        return athlete


def _create_completed_category(
    tournament_id: int,
    *,
    name: str,
    first_place_id: int,
    modality: str = Modality.KUMITE_INDIVIDUAL.value,
    competition_system: str = CompetitionSystem.ELIMINATION.value,
) -> TournamentCategory:
    with rx.session() as session:
        category = TournamentCategory(
            name=name,
            modality=modality,
            gender="MIXED",
            min_age=16,
            max_age=40,
            competition_system=competition_system,
            bracket_size=8,
            status=CategoryStatus.COMPLETED.value,
            tournament_id=tournament_id,
            first_place_id=first_place_id,
        )
        session.add(category)
        session.commit()
        session.refresh(category)
        return category


class TestDashboardStateLoadRecentWinners:
    """DashboardState.load_recent_winners delegates to ResultsService."""

    @pytest.mark.anyio
    async def test_load_recent_winners_empty(self) -> None:
        """Called with no data → winner_cards == [], is_loading == False."""
        from kakumi_app.states.dashboard_state import DashboardState

        state = DashboardState()
        mock_auth = MagicMock()
        mock_auth.is_authenticated = True
        object.__setattr__(state, "get_state", AsyncMock(return_value=mock_auth))
        await DashboardState.load_recent_winners.fn(state)

        assert state.winner_cards == []
        assert state.is_loading is False

    @pytest.mark.anyio
    async def test_load_recent_winners_populates_cards(self) -> None:
        """DB has 2 winners → len(winner_cards) == 2, fields match."""
        from kakumi_app.states.dashboard_state import DashboardState

        tournament = _create_tournament(name="Dash Cup")
        a1 = _create_athlete(name="Ana Winner")
        a2 = _create_athlete(name="Luis Champ")
        cat1 = _create_completed_category(
            tournament.id,
            name="Kumite Fem",
            first_place_id=a1.id,
        )
        cat2 = _create_completed_category(
            tournament.id,
            name="Kumite Masc",
            first_place_id=a2.id,
        )
        # Create completed matches for both categories
        for cat_id, athlete_id in [(cat1.id, a1.id), (cat2.id, a2.id)]:
            with rx.session() as session:
                match = Match(
                    category_id=cat_id,
                    round=1,
                    match_number=1,
                    position=1,
                    match_type=MatchType.FINAL.value,
                    status=MatchStatus.COMPLETED.value,
                    aka_id=athlete_id,
                    aka_score=5,
                    ao_score=0,
                    winner_id=athlete_id,
                )
                session.add(match)
                session.commit()

        state = DashboardState()
        mock_auth = MagicMock()
        mock_auth.is_authenticated = True
        object.__setattr__(state, "get_state", AsyncMock(return_value=mock_auth))
        await DashboardState.load_recent_winners.fn(state)

        assert len(state.winner_cards) == 2
        names = {c["winner_name"] for c in state.winner_cards}
        assert names == {"Ana Winner", "Luis Champ"}
        assert state.is_loading is False

    @pytest.mark.anyio
    async def test_load_recent_winners_handles_error(self, monkeypatch) -> None:
        """Monkeypatch service to raise → winner_cards == [], is_loading == False."""
        from kakumi_app.services import results_service
        from kakumi_app.states.dashboard_state import DashboardState

        def _raise_error():
            raise RuntimeError("DB boom")

        monkeypatch.setattr(
            results_service.ResultsService,
            "get_recent_winners",
            _raise_error,
        )

        state = DashboardState()
        mock_auth = MagicMock()
        mock_auth.is_authenticated = True
        object.__setattr__(state, "get_state", AsyncMock(return_value=mock_auth))
        await DashboardState.load_recent_winners.fn(state)

        assert state.winner_cards == []
        assert state.is_loading is False
