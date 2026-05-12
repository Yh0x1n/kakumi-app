"""Tests for Slice 1 bracket state loading."""

import datetime

import pytest
import reflex as rx
from reflex.istate.data import PageData
from sqlmodel import Session as SQLModelSession

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.tournament_model import Match, MatchType, TournamentCategory
from kakumi_app.states.bracket_state import BracketState


def _set_route_param(state: BracketState, key: str, value: str) -> None:
    object.__setattr__(state.router, "_page", PageData(params={key: value}))


def _create_match_with_participants(
    category_id: int,
    tournament_id: int,
    *,
    aka_name: str,
    ao_name: str,
) -> Match:
    with rx.session() as session:
        aka = Athlete(
            name=aka_name,
            date_of_birth=datetime.date(2000, 1, 1),
            gender="MALE",
            email=f"{aka_name.lower().replace(' ', '-')}-bracket@test.local",
            license_number=f"LIC-{aka_name.lower().replace(' ', '-')}",
            kata_category_id=category_id,
        )
        ao = Athlete(
            name=ao_name,
            date_of_birth=datetime.date(2001, 2, 2),
            gender="FEMALE",
            email=f"{ao_name.lower().replace(' ', '-')}-bracket@test.local",
            license_number=f"LIC-{ao_name.lower().replace(' ', '-')}",
            kata_category_id=category_id,
        )
        session.add(aka)
        session.add(ao)
        session.commit()
        session.refresh(aka)
        session.refresh(ao)

        match = Match(
            tournament_id=tournament_id,
            category_id=category_id,
            round=1,
            position=1,
            match_number=1,
            match_type=MatchType.ELIMINATION.value,
            status="READY",
            aka_id=aka.id,
            ao_id=ao.id,
        )
        session.add(match)
        session.commit()
        session.refresh(match)
        return match


@pytest.mark.anyio
async def test_load_bracket_valid_tournament_loads_categories_and_grouped_matches(
    sample_tournament,
    sample_category,
) -> None:
    _create_match_with_participants(
        sample_category.id,
        sample_tournament.id,
        aka_name="Aka Visible",
        ao_name="Ao Visible",
    )
    state = BracketState()
    _set_route_param(state, "id", str(sample_tournament.id))

    await BracketState.load_bracket.fn(state)

    assert state.error_message == ""
    assert state.tournament["id"] == sample_tournament.id
    assert len(state.categories) == 1
    assert state.categories[0]["id"] == sample_category.id
    assert state.categories[0]["rounds"][0]["matches"][0]["aka_label"] == "Aka Visible"
    assert state.categories[0]["rounds"][0]["matches"][0]["ao_label"] == "Ao Visible"


@pytest.mark.anyio
@pytest.mark.parametrize("params", [{}, {"id": "abc"}, {"id": ""}])
async def test_load_bracket_invalid_or_missing_route_param_sets_safe_error(
    params: dict[str, str],
) -> None:
    state = BracketState()
    object.__setattr__(state.router, "_page", PageData(params=params))

    await BracketState.load_bracket.fn(state)

    assert state.tournament == {}
    assert state.categories == []
    assert state.error_message != ""
    assert state.is_loading is False


@pytest.mark.anyio
async def test_load_bracket_missing_tournament_sets_not_found_error() -> None:
    state = BracketState()
    _set_route_param(state, "id", "999999")

    await BracketState.load_bracket.fn(state)

    assert state.tournament == {}
    assert state.categories == []
    assert "no encontrado" in state.error_message.lower()


@pytest.mark.anyio
async def test_load_bracket_category_without_matches_is_empty_but_not_error(
    sample_tournament,
) -> None:
    with rx.session() as session:
        empty_category = TournamentCategory(
            name="Categoría Vacía",
            modality="KATA_INDIVIDUAL",
            gender="MIXED",
            min_age=10,
            max_age=50,
            competition_system="ELIMINATION",
            bracket_size=8,
            tournament_id=sample_tournament.id,
        )
        session.add(empty_category)
        session.commit()
        session.refresh(empty_category)

    state = BracketState()
    _set_route_param(state, "id", str(sample_tournament.id))

    await BracketState.load_bracket.fn(state)

    assert state.error_message == ""
    assert len(state.categories) == 1
    assert state.categories[0]["id"] == empty_category.id
    assert state.categories[0]["rounds"] == []


@pytest.mark.anyio
async def test_load_bracket_db_failure_sets_generic_safe_error(
    monkeypatch: pytest.MonkeyPatch,
    sample_tournament,
) -> None:
    state = BracketState()
    _set_route_param(state, "id", str(sample_tournament.id))

    def _broken_get(self, entity, ident, **kwargs):
        raise RuntimeError("db offline")

    monkeypatch.setattr(SQLModelSession, "get", _broken_get)

    await BracketState.load_bracket.fn(state)

    assert state.tournament == {}
    assert state.categories == []
    assert state.error_message == "Error cargando datos"
    assert state.is_loading is False
