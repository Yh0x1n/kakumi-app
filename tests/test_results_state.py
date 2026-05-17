"""Results state tests (repo convention: tests live under `tests/`)."""

from __future__ import annotations

import pytest
from reflex.istate.data import PageData

from kakumi_app.states.results_state import ResultsState


def _set_route_id(state: ResultsState, value: str) -> None:
    object.__setattr__(state.router, "_page", PageData(params={"id": value}))


def test_parse_route_id_accepts_numeric_values() -> None:
    state = ResultsState()
    _set_route_id(state, "42")

    assert state._parse_route_id() == 42


@pytest.mark.parametrize("params", [{}, {"id": "abc"}, {"id": ""}])
def test_parse_route_id_rejects_invalid_values(params: dict[str, str]) -> None:
    state = ResultsState()
    object.__setattr__(state.router, "_page", PageData(params=params))

    with pytest.raises(ValueError):
        state._parse_route_id()


@pytest.mark.anyio
async def test_load_results_index_populates_tournaments_and_clears_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = ResultsState()

    monkeypatch.setattr(
        "kakumi_app.states.results_state.ResultsService.list_tournament_cards",
        lambda: [{"id": 7, "name": "Open Kakumi"}],
    )

    await ResultsState.load_results_index.fn(state)

    assert state.error_message == ""
    assert state.tournaments == [{"id": 7, "name": "Open Kakumi"}]
    assert state.is_loading is False


@pytest.mark.anyio
async def test_load_results_index_handles_service_error_with_safe_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = ResultsState()

    def _boom() -> list[dict[str, object]]:
        raise RuntimeError("db offline")

    monkeypatch.setattr(
        "kakumi_app.states.results_state.ResultsService.list_tournament_cards",
        _boom,
    )

    await ResultsState.load_results_index.fn(state)

    assert state.tournaments == []
    assert state.error_message == "Error cargando resultados"
    assert state.is_loading is False


@pytest.mark.anyio
async def test_load_tournament_view_rejects_invalid_route_id() -> None:
    state = ResultsState()
    _set_route_id(state, "abc")

    await ResultsState.load_tournament_view.fn(state)

    assert state.current_tournament == {}
    assert state.categories == []
    assert state.error_message == "ID de torneo inválido"


@pytest.mark.anyio
async def test_load_tournament_view_populates_summary_and_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = ResultsState()
    _set_route_id(state, "9")

    monkeypatch.setattr(
        "kakumi_app.states.results_state.ResultsService.get_tournament_view",
        lambda tournament_id: {
            "tournament": {"id": tournament_id, "name": "Open Hub"},
            "summary": {"total_categories": 1},
            "categories": [{"id": 99, "name": "Kata Senior"}],
        },
    )

    await ResultsState.load_tournament_view.fn(state)

    assert state.error_message == ""
    assert state.current_tournament["id"] == 9
    assert state.tournament_summary["total_categories"] == 1
    assert state.categories[0]["id"] == 99


@pytest.mark.anyio
async def test_load_category_view_invalid_id_sets_error() -> None:
    """Invalid route id sets error_message on category view."""
    state = ResultsState()
    _set_route_id(state, "xyz")

    await ResultsState.load_category_view.fn(state)

    assert state.error_message != ""
    assert state.current_category == {}


@pytest.mark.anyio
async def test_load_category_view_populates_category_and_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid route id populates current_category and category_data."""
    state = ResultsState()
    _set_route_id(state, "5")

    monkeypatch.setattr(
        "kakumi_app.states.results_state.ResultsService.get_category_view",
        lambda category_id: {
            "category": {"id": 5, "name": "Kata Senior", "modality": "KATA_INDIVIDUAL"},
            "matches": [{"id": 10, "round": 1}],
            "standings": None,
        },
    )

    await ResultsState.load_category_view.fn(state)

    assert state.error_message == ""
    assert state.current_category["id"] == 5
    assert state.current_category["name"] == "Kata Senior"


@pytest.mark.anyio
async def test_load_category_view_handles_service_error_with_safe_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Service error in category view resets state and sets error."""
    state = ResultsState()
    _set_route_id(state, "7")

    def _boom(category_id: int) -> dict:
        raise RuntimeError("service down")

    monkeypatch.setattr(
        "kakumi_app.states.results_state.ResultsService.get_category_view",
        _boom,
    )

    await ResultsState.load_category_view.fn(state)

    assert state.current_category == {}
    assert state.category_standings == []
    assert state.category_matches == []
    assert state.error_message == "Error cargando resultados"


# ==============================================================================
# Slice 3 — Podios / Statistics state tests
# ==============================================================================


def _set_tournament_param(state: ResultsState, value: str | None) -> None:
    """Set tournament_id in route params for testing."""
    params: dict[str, str] = {}
    if value is not None:
        params["tournament_id"] = value
    object.__setattr__(state.router, "_page", PageData(params=params))


def test_parse_context_tournament_id_valid() -> None:
    state = ResultsState()
    _set_tournament_param(state, "5")
    assert state._parse_context_tournament_id() == 5


def test_parse_context_tournament_id_absent() -> None:
    state = ResultsState()
    _set_tournament_param(state, None)
    assert state._parse_context_tournament_id() is None


def test_parse_context_tournament_id_invalid() -> None:
    state = ResultsState()
    _set_tournament_param(state, "abc")
    assert state._parse_context_tournament_id() is None


@pytest.mark.anyio
async def test_load_podiums_view_populates_cards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = ResultsState()
    _set_tournament_param(state, "3")

    monkeypatch.setattr(
        "kakumi_app.states.results_state.ResultsService.get_podiums_view",
        lambda tid: {"categories": [{"name": "Podio 1", "podium_status": "available"}]},
    )

    await ResultsState.load_podiums_view.fn(state)

    assert state.error_message == ""
    assert len(state.podium_cards) == 1
    assert state.podium_cards[0]["name"] == "Podio 1"


@pytest.mark.anyio
async def test_load_podiums_view_no_context() -> None:
    state = ResultsState()
    _set_tournament_param(state, None)

    await ResultsState.load_podiums_view.fn(state)

    assert state.error_message != ""
    assert state.podium_cards == []


@pytest.mark.anyio
async def test_load_statistics_view_populates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = ResultsState()
    _set_tournament_param(state, "4")

    monkeypatch.setattr(
        "kakumi_app.states.results_state.ResultsService.get_statistics_view",
        lambda tid: {"total_categories": 2, "total_matches": 5},
    )

    await ResultsState.load_statistics_view.fn(state)

    assert state.error_message == ""
    assert state.statistics_view["total_categories"] == 2
    assert state.statistics_view["total_matches"] == 5


# ==============================================================================
# Triangulation — edge cases for podiums/statistics state handlers
# ==============================================================================


@pytest.mark.anyio
async def test_load_podiums_view_handles_service_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Service error in load_podiums_view resets and sets error."""
    state = ResultsState()
    _set_tournament_param(state, "7")

    def _boom(tid: int) -> dict:
        raise RuntimeError("service error")

    monkeypatch.setattr(
        "kakumi_app.states.results_state.ResultsService.get_podiums_view",
        _boom,
    )

    await ResultsState.load_podiums_view.fn(state)

    assert state.podium_cards == []
    assert state.error_message != ""


@pytest.mark.anyio
async def test_load_statistics_view_no_context() -> None:
    """No tournament_id in context → error message."""
    state = ResultsState()
    _set_tournament_param(state, None)

    await ResultsState.load_statistics_view.fn(state)

    assert state.error_message != ""
    assert state.statistics_view == {}


@pytest.mark.anyio
async def test_load_statistics_view_handles_service_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Service error in load_statistics_view resets and sets error."""
    state = ResultsState()
    _set_tournament_param(state, "8")

    def _boom(tid: int) -> dict:
        raise RuntimeError("db error")

    monkeypatch.setattr(
        "kakumi_app.states.results_state.ResultsService.get_statistics_view",
        _boom,
    )

    await ResultsState.load_statistics_view.fn(state)

    assert state.statistics_view == {}
    assert state.modality_breakdown == []
    assert state.system_breakdown == []
    assert state.match_status_breakdown == []
    assert state.error_message != ""
