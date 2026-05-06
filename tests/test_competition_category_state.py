"""Tests for Slice 1 competition category state loading."""

import datetime

import pytest
import reflex as rx
from reflex.istate.data import PageData
from sqlmodel import Session as SQLModelSession

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.referee_model import LicenseLevel, Referee, RefereeRole
from kakumi_app.models.tournament_model import Match, MatchType, Tatami
from kakumi_app.states.competition_category_state import CompetitionCategoryState


def _set_route_param(
    state: CompetitionCategoryState, key: str, value: str | None = None
) -> None:
    params = {} if value is None else {key: value}
    object.__setattr__(state.router, "_page", PageData(params=params))


def _create_category_match_bundle(category_id: int, tournament_id: int) -> None:
    with rx.session() as session:
        aka = Athlete(
            name="Operador Aka",
            date_of_birth=datetime.date(2001, 3, 1),
            gender="MALE",
            email="operador-aka@test.local",
            license_number="OPERADOR-AKA-1",
            kata_category_id=category_id,
        )
        ao = Athlete(
            name="Operador Ao",
            date_of_birth=datetime.date(2002, 4, 2),
            gender="FEMALE",
            email="operador-ao@test.local",
            license_number="OPERADOR-AO-1",
            kata_category_id=category_id,
        )
        session.add(aka)
        session.add(ao)
        session.commit()
        session.refresh(aka)
        session.refresh(ao)

        tatami = Tatami(name="Tatami Central", tournament_id=tournament_id)
        referee = Referee(
            name="Ref Principal",
            license_number="REF-PRINCIPAL-1",
            license_level=LicenseLevel.NATIONAL.value,
            role=RefereeRole.REFEREE.value,
        )
        session.add(tatami)
        session.add(referee)
        session.commit()
        session.refresh(tatami)
        session.refresh(referee)

        session.add(
            Match(
                tournament_id=tournament_id,
                category_id=category_id,
                round=2,
                position=2,
                match_number=2,
                match_type=MatchType.ELIMINATION.value,
                status="IN_PROGRESS",
                aka_id=aka.id,
                ao_id=ao.id,
                tatami_id=tatami.id,
                referee_id=referee.id,
            )
        )
        session.add(
            Match(
                tournament_id=tournament_id,
                category_id=category_id,
                round=3,
                position=1,
                match_number=1,
                match_type=MatchType.FINAL.value,
                status="PENDING",
                aka_id=aka.id,
                ao_id=None,
            )
        )
        session.commit()


@pytest.mark.anyio
async def test_load_category_valid_category_returns_sorted_match_list(
    sample_tournament,
    sample_category,
) -> None:
    _create_category_match_bundle(sample_category.id, sample_tournament.id)
    state = CompetitionCategoryState()
    _set_route_param(state, "category_id", str(sample_category.id))

    await CompetitionCategoryState.load_category.fn(state)

    assert state.error_message == ""
    assert state.category["id"] == sample_category.id
    assert [(match["round"], match["position"]) for match in state.matches] == [
        (2, 2),
        (3, 1),
    ]
    assert state.matches[0]["status"] == "IN_PROGRESS"
    assert state.matches[0]["tatami_label"] == "Tatami Central"
    assert state.matches[0]["referee_label"] == "Ref Principal"


@pytest.mark.anyio
@pytest.mark.parametrize("params", [{}, {"category_id": "oops"}, {"category_id": ""}])
async def test_load_category_invalid_or_missing_route_param_sets_safe_error(
    params: dict[str, str],
) -> None:
    state = CompetitionCategoryState()
    object.__setattr__(state.router, "_page", PageData(params=params))

    await CompetitionCategoryState.load_category.fn(state)

    assert state.category == {}
    assert state.matches == []
    assert state.error_message != ""
    assert state.is_loading is False


@pytest.mark.anyio
async def test_load_category_missing_category_sets_not_found_error() -> None:
    state = CompetitionCategoryState()
    _set_route_param(state, "category_id", "999999")

    await CompetitionCategoryState.load_category.fn(state)

    assert state.category == {}
    assert state.matches == []
    assert "no encontrada" in state.error_message.lower()


@pytest.mark.anyio
async def test_load_category_without_matches_is_empty_but_not_error(
    sample_category,
) -> None:
    state = CompetitionCategoryState()
    _set_route_param(state, "category_id", str(sample_category.id))

    await CompetitionCategoryState.load_category.fn(state)

    assert state.error_message == ""
    assert state.category["id"] == sample_category.id
    assert state.matches == []


@pytest.mark.anyio
async def test_load_category_missing_tatami_or_referee_uses_safe_none_labels(
    sample_tournament,
    sample_category,
) -> None:
    _create_category_match_bundle(sample_category.id, sample_tournament.id)
    state = CompetitionCategoryState()
    _set_route_param(state, "category_id", str(sample_category.id))

    await CompetitionCategoryState.load_category.fn(state)

    assert state.matches[1]["aka_label"] == "Operador Aka"
    assert state.matches[1]["ao_label"] == "TBD"
    assert state.matches[1]["tatami_label"] is None
    assert state.matches[1]["referee_label"] is None


@pytest.mark.anyio
async def test_load_category_exposes_pending_match_live_route_for_start_cta(
    sample_tournament,
    sample_category,
) -> None:
    _create_category_match_bundle(sample_category.id, sample_tournament.id)
    state = CompetitionCategoryState()
    _set_route_param(state, "category_id", str(sample_category.id))

    await CompetitionCategoryState.load_category.fn(state)

    pending_match = next(
        match for match in state.matches if match["status"] == "PENDING"
    )
    assert pending_match["live_match_href"] == (
        f"/competition/kumite/match/{pending_match['id']}"
    )


@pytest.mark.anyio
async def test_load_category_non_pending_match_hides_live_route_handoff(
    sample_tournament,
    sample_category,
) -> None:
    _create_category_match_bundle(sample_category.id, sample_tournament.id)
    state = CompetitionCategoryState()
    _set_route_param(state, "category_id", str(sample_category.id))

    await CompetitionCategoryState.load_category.fn(state)

    in_progress_match = next(
        match for match in state.matches if match["status"] == "IN_PROGRESS"
    )
    assert in_progress_match["live_match_href"] is None


@pytest.mark.anyio
async def test_load_category_db_failure_sets_generic_safe_error(
    monkeypatch: pytest.MonkeyPatch,
    sample_category,
) -> None:
    state = CompetitionCategoryState()
    _set_route_param(state, "category_id", str(sample_category.id))

    def _broken_get(self, entity, ident, **kwargs):
        raise RuntimeError("db offline")

    monkeypatch.setattr(SQLModelSession, "get", _broken_get)

    await CompetitionCategoryState.load_category.fn(state)

    assert state.category == {}
    assert state.matches == []
    assert state.error_message == "Error cargando datos"
    assert state.is_loading is False
