"""Tests for ViewerState bracket loading — viewer-bracket-live change.

Tests verify that:
- load_category_bracket loads bracket_data for valid category with matches
- load_category_bracket handles empty categories gracefully
- load_category_bracket does nothing when no category is selected
"""

import datetime

import pytest
import reflex as rx

from kakumi_app.models.tournament_model import (
    CategoryStatus,
    CompetitionSystem,
    Match,
    MatchStatus,
    MatchType,
    Modality,
    Tournament,
    TournamentCategory,
    TournamentStatus,
)
from kakumi_app.states.viewer_state import ViewerState


@pytest.mark.asyncio
async def test_load_category_bracket_with_matches(
    db_session,
    sample_user,
) -> None:
    """load_category_bracket builds bracket_data for category with matches."""
    with rx.session() as session:
        tournament = Tournament(
            name="Bracket Test",
            venue="Dojo",
            start_date=datetime.date(2026, 7, 1),
            end_date=datetime.date(2026, 7, 3),
            tatami_count=1,
            status=TournamentStatus.PLANIFICADO.value,
            is_public=True,
            created_by_id=sample_user.id,
        )
        session.add(tournament)
        session.commit()
        session.refresh(tournament)

        category = TournamentCategory(
            name="Kata Individual Masculino",
            modality=Modality.KATA_INDIVIDUAL.value,
            competition_system=CompetitionSystem.ELIMINATION.value,
            bracket_size=4,
            status=CategoryStatus.PENDING.value,
            tournament_id=tournament.id,
        )
        session.add(category)
        session.commit()
        session.refresh(category)

        match = Match(
            round=1,
            match_number=1,
            position=1,
            match_type=MatchType.ELIMINATION.value,
            category_id=category.id,
            tournament_id=tournament.id,
            aka_score=3,
            ao_score=1,
            status=MatchStatus.COMPLETED.value,
        )
        session.add(match)
        session.commit()
        session.refresh(match)
        match_id = match.id
        category_id = category.id

    state = ViewerState()  # type: ignore[call-arg]
    state.selected_category_id = category_id
    state.selected_category_type = "kata"

    await state.load_category_bracket()

    assert state.bracket_data is not None
    assert state.bracket_data["id"] == category.id
    assert state.bracket_data["name"] == category.name
    assert state.bracket_data["modality"] == Modality.KATA_INDIVIDUAL.value
    assert "rounds" in state.bracket_data
    assert len(state.bracket_data["rounds"]) > 0
    first_round = state.bracket_data["rounds"][0]
    assert first_round["round"] == 1
    assert len(first_round["matches"]) == 1
    assert first_round["matches"][0]["id"] == match_id
    assert first_round["matches"][0]["aka_score"] == 3
    assert first_round["matches"][0]["ao_score"] == 1
    assert not state.is_loading_bracket


@pytest.mark.asyncio
async def test_load_category_bracket_empty_category(
    db_session,
    sample_user,
) -> None:
    """load_category_bracket builds bracket with empty rounds for empty category."""
    with rx.session() as session:
        tournament = Tournament(
            name="Empty Bracket Test",
            venue="Dojo",
            start_date=datetime.date(2026, 7, 1),
            end_date=datetime.date(2026, 7, 3),
            tatami_count=1,
            status=TournamentStatus.PLANIFICADO.value,
            is_public=True,
            created_by_id=sample_user.id,
        )
        session.add(tournament)
        session.commit()
        session.refresh(tournament)

        category = TournamentCategory(
            name="Empty Category",
            modality=Modality.KATA_INDIVIDUAL.value,
            competition_system=CompetitionSystem.ELIMINATION.value,
            bracket_size=4,
            status=CategoryStatus.PENDING.value,
            tournament_id=tournament.id,
        )
        session.add(category)
        session.commit()
        session.refresh(category)
        category_id = category.id

    state = ViewerState()  # type: ignore[call-arg]
    state.selected_category_id = category_id
    state.selected_category_type = "kata"

    await state.load_category_bracket()

    assert state.bracket_data is not None
    assert state.bracket_data["id"] == category.id
    assert "rounds" in state.bracket_data
    assert len(state.bracket_data["rounds"]) == 0
    assert not state.is_loading_bracket


@pytest.mark.asyncio
async def test_load_category_bracket_no_selection() -> None:
    """load_category_bracket does nothing when no category selected."""
    state = ViewerState()  # type: ignore[call-arg]
    state.selected_category_id = None

    await state.load_category_bracket()

    assert state.bracket_data is None
    assert not state.is_loading_bracket
