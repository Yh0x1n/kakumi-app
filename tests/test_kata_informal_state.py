"""Tests for dedicated informal Kata state flow."""

from __future__ import annotations

import pytest
import reflex as rx
from reflex.istate.data import PageData

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.tournament_model import (
    CategoryGender,
    CategoryStatus,
    CompetitionSystem,
    Modality,
    TournamentCategory,
)
from kakumi_app.states.kata_informal_state import KataInformalState


def _set_route_category(state: KataInformalState, category_id: int) -> None:
    object.__setattr__(state.router, "_page", PageData(params={"id": str(category_id)}))


def _create_informal_category(tournament_id: int) -> TournamentCategory:
    with rx.session() as session:
        category = TournamentCategory(
            name="Kata Informal State",
            modality=Modality.KATA_INDIVIDUAL.value,
            gender=CategoryGender.MIXED.value,
            min_age=16,
            max_age=40,
            competition_system=CompetitionSystem.ROUND_ROBIN.value,
            bracket_size=8,
            status=CategoryStatus.IN_PROGRESS.value,
            tournament_id=tournament_id,
            judge_panel_size=5,
            kata_flow_mode="INFORMAL",
        )
        session.add(category)
        session.commit()
        session.refresh(category)
        return category


def _create_athlete(name: str, email: str, category_id: int) -> Athlete:
    with rx.session() as session:
        athlete = Athlete(
            name=name,
            age=26,
            gender="MALE",
            email=email,
            belt_rank="Negro",
            is_active=True,
        )
        session.add(athlete)
        session.commit()
        session.refresh(athlete)
        return athlete


@pytest.mark.anyio
async def test_load_category_session_reads_roster(sample_tournament) -> None:
    category = _create_informal_category(sample_tournament.id)
    athlete = _create_athlete("State Athlete", "state-athlete@test.local", category.id)
    state = KataInformalState()
    _set_route_category(state, category.id)

    await KataInformalState.load_category_session.fn(state)

    assert state.category_id == category.id
    assert state.error_message == ""
    assert any(row["id"] == athlete.id for row in state.roster)


@pytest.mark.anyio
async def test_finalize_performance_requires_complete_panel(sample_tournament) -> None:
    category = _create_informal_category(sample_tournament.id)
    athlete = _create_athlete("Panel Athlete", "panel-athlete@test.local", category.id)
    state = KataInformalState()
    _set_route_category(state, category.id)
    await KataInformalState.load_category_session.fn(state)

    await KataInformalState.select_athlete.fn(state, str(athlete.id))
    await KataInformalState.set_judge_score.fn(state, "J1", "8.0")

    await KataInformalState.finalize_performance.fn(state)

    assert "Panel incompleto" in state.error_message


@pytest.mark.anyio
async def test_finalize_performance_saves_and_refreshes_standings(
    sample_tournament,
) -> None:
    category = _create_informal_category(sample_tournament.id)
    athlete = _create_athlete("Score Athlete", "score-athlete@test.local", category.id)
    state = KataInformalState()
    _set_route_category(state, category.id)
    await KataInformalState.load_category_session.fn(state)

    await KataInformalState.select_athlete.fn(state, str(athlete.id))
    for slot, value in zip(["J1", "J2", "J3", "J4", "J5"], ["8.0"] * 5):
        await KataInformalState.set_judge_score.fn(state, slot, value)

    await KataInformalState.finalize_performance.fn(state)

    assert state.error_message == ""
    assert len(state.standings) == 1
    assert state.standings[0]["athlete_id"] == athlete.id


@pytest.mark.anyio
async def test_standings_include_victory_points_field(sample_tournament) -> None:
    from kakumi_app.services.kata_informal_service import KataInformalService

    category = _create_informal_category(sample_tournament.id)
    athlete = _create_athlete(
        "Points Athlete", "points-athlete@test.local", category.id
    )
    KataInformalService.save_performance(
        category_id=category.id,
        athlete_id=athlete.id,
        judge_scores=[8.0, 8.0, 8.0, 8.0, 8.0],
    )
    state = KataInformalState()
    _set_route_category(state, category.id)

    await KataInformalState.load_category_session.fn(state)

    assert isinstance(state.standings, list)
    assert len(state.standings) == 1
    assert "victory_points" in state.standings[0]


@pytest.mark.anyio
async def test_finalize_performance_advances_to_next_athlete_and_resets_panel(
    sample_tournament,
) -> None:
    category = _create_informal_category(sample_tournament.id)
    first = _create_athlete("Alpha", "alpha@test.local", category.id)
    second = _create_athlete("Beta", "beta@test.local", category.id)
    state = KataInformalState()
    _set_route_category(state, category.id)

    await KataInformalState.load_category_session.fn(state)

    assert state.selected_athlete_id == first.id

    for slot in ("J1", "J2", "J3", "J4", "J5"):
        await KataInformalState.set_judge_score.fn(state, slot, "8.0")

    await KataInformalState.finalize_performance.fn(state)

    assert state.error_message == ""
    assert state.selected_athlete_id == second.id
    assert state.judge_entries == {"J1": "", "J2": "", "J3": "", "J4": "", "J5": ""}
    assert len(state.standings) == 1
