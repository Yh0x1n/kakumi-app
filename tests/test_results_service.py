"""Results service tests (repo convention: tests live under `tests/`)."""

from __future__ import annotations

import datetime

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
from kakumi_app.services.results_service import ResultsService


def _create_tournament(*, name: str) -> Tournament:
    with rx.session() as session:
        tournament = Tournament(
            name=name,
            venue="Dojo Resultados",
            start_date=datetime.date(2026, 10, 1),
            end_date=datetime.date(2026, 10, 2),
            tatami_count=2,
            status="PLANIFICADO",
            is_public=True,
        )
        session.add(tournament)
        session.commit()
        session.refresh(tournament)
        return tournament


def _create_category(
    tournament_id: int,
    *,
    name: str,
    status: str = CategoryStatus.PENDING.value,
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
            status=status,
            tournament_id=tournament_id,
        )
        session.add(category)
        session.commit()
        session.refresh(category)
        return category


def _create_match(
    category_id: int,
    *,
    status: str,
    tournament_id: int | None = None,
) -> Match:
    with rx.session() as session:
        match = Match(
            round=1,
            match_number=1,
            position=1,
            match_type=MatchType.ELIMINATION.value,
            tournament_id=tournament_id,
            category_id=category_id,
            status=status,
        )
        session.add(match)
        session.commit()
        session.refresh(match)
        return match


def test_list_tournament_cards_returns_empty_when_no_tournaments() -> None:
    assert ResultsService.list_tournament_cards() == []


def test_list_tournament_cards_aggregates_category_and_match_counts() -> None:
    tournament = _create_tournament(name="Torneo Card")
    category = _create_category(
        tournament.id,
        name="Kumite Card",
        status=CategoryStatus.COMPLETED.value,
    )
    _create_match(category.id, status=MatchStatus.COMPLETED.value)
    _create_match(category.id, status=MatchStatus.PENDING.value)

    cards = ResultsService.list_tournament_cards()

    assert len(cards) == 1
    assert cards[0]["id"] == tournament.id
    assert cards[0]["category_count"] == 1
    assert cards[0]["completed_category_count"] == 1
    assert cards[0]["total_match_count"] == 2
    assert cards[0]["completed_match_count"] == 1


def test_get_tournament_view_aggregates_matches_through_category_ids_only(
    sample_tournament,
) -> None:
    category = _create_category(
        sample_tournament.id,
        name="Categoría Hub",
        status=CategoryStatus.IN_PROGRESS.value,
    )
    _create_match(
        category.id,
        status=MatchStatus.COMPLETED.value,
        tournament_id=None,
    )
    _create_match(
        category.id,
        status=MatchStatus.PENDING.value,
        tournament_id=None,
    )

    view = ResultsService.get_tournament_view(sample_tournament.id)

    assert view["summary"]["total_categories"] == 1
    assert view["summary"]["total_matches"] == 2
    assert view["summary"]["completed_matches"] == 1
    assert view["categories"][0]["total_match_count"] == 2
    assert view["categories"][0]["completed_match_count"] == 1


@pytest.mark.parametrize("invalid_id", [0, -10, 999999])
def test_get_tournament_view_invalid_id_raises_value_error(invalid_id: int) -> None:
    with pytest.raises(ValueError):
        ResultsService.get_tournament_view(invalid_id)


def test_get_category_view_returns_kata_informal_standings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Kata informal category uses KataInformalService.rank_category()."""
    tournament = _create_tournament(name="Torneo Kata")
    category = _create_category(
        tournament.id,
        name="Kata Informal RR",
        status=CategoryStatus.PENDING.value,
        modality=Modality.KATA_INDIVIDUAL.value,
        competition_system=CompetitionSystem.ROUND_ROBIN.value,
    )

    fake_standings = [
        {"athlete_id": 1, "name": "Athlete A", "total_score": 25.5},
        {"athlete_id": 2, "name": "Athlete B", "total_score": 24.0},
    ]

    monkeypatch.setattr(
        "kakumi_app.services.results_service."  # noqa: ISC001
        "KataInformalService.rank_category",
        lambda cat_id: fake_standings,
    )

    result = ResultsService.get_category_view(category.id)

    assert result["category"]["id"] == category.id
    assert result["category"]["name"] == "Kata Informal RR"
    assert result["category"]["modality"] == Modality.KATA_INDIVIDUAL.value
    assert result["category"]["competition_system"] == CompetitionSystem.ROUND_ROBIN.value
    assert result["standings"] == fake_standings
    assert result["matches"] == []


def test_get_category_view_returns_match_summaries_for_standard_category() -> None:
    """Standard elimination category returns ordered match summaries."""
    tournament = _create_tournament(name="Torneo Standard")
    category = _create_category(
        tournament.id,
        name="Kumite Estandar",
        status=CategoryStatus.IN_PROGRESS.value,
    )
    match1 = _create_match(category.id, status=MatchStatus.COMPLETED.value)
    match2 = _create_match(category.id, status=MatchStatus.PENDING.value)

    result = ResultsService.get_category_view(category.id)

    assert result["category"]["id"] == category.id
    assert result["category"]["name"] == "Kumite Estandar"
    assert len(result["matches"]) == 2
    assert result["standings"] is None
    assert result["matches"][0]["id"] in (match1.id, match2.id)
    assert result["matches"][1]["id"] in (match1.id, match2.id)


@pytest.mark.parametrize("invalid_id", [0, -10, 999999])
def test_get_category_view_invalid_id_raises_value_error(invalid_id: int) -> None:
    """Invalid category id raises ValueError."""
    with pytest.raises(ValueError):
        ResultsService.get_category_view(invalid_id)


def test_get_category_view_empty_matches_shows_message() -> None:
    """Category without matches returns empty message."""
    tournament = _create_tournament(name="Torneo Vacio")
    category = _create_category(
        tournament.id,
        name="Categoría Sin Encuentros",
    )

    result = ResultsService.get_category_view(category.id)

    assert result["category"]["id"] == category.id
    assert result["matches"] == []
    assert result["standings"] is None
    assert result["empty_message"] != ""


# ==============================================================================
# Podios / Statistics — Slice 3 RED tests
# ==============================================================================


def _create_athlete_for_test(*, name: str) -> Athlete:
    """Create an athlete in the test DB."""
    with rx.session() as session:
        athlete = Athlete(
            name=name,
            date_of_birth=datetime.date(1995, 6, 15),
            gender="MALE",
            email=f"{name.lower().replace(' ','')}@test.com",
        )
        session.add(athlete)
        session.commit()
        session.refresh(athlete)
        return athlete


def test_get_podiums_view_available() -> None:
    """COMPLETED category with first+second+third place → available."""
    tournament = _create_tournament(name="Podios Available")
    a1 = _create_athlete_for_test(name="Ana Oro")
    a2 = _create_athlete_for_test(name="Luis Plata")
    a3 = _create_athlete_for_test(name="Eva Bronce")
    category = _create_category(
        tournament.id,
        name="Kumite Ind",
        status=CategoryStatus.COMPLETED.value,
    )
    with rx.session() as session:
        db_cat = session.get(TournamentCategory, category.id)
        assert db_cat is not None
        db_cat.first_place_id = a1.id
        db_cat.second_place_id = a2.id
        db_cat.third_place_ids = str([a3.id])
        session.add(db_cat)
        session.commit()

    result = ResultsService.get_podiums_view(tournament.id)
    cards = result.get("categories", [])
    assert len(cards) == 1
    card = cards[0]
    assert card["podium_status"] == "available"
    assert card["first_place_name"] == "Ana Oro"
    assert card["second_place_name"] == "Luis Plata"
    assert card["third_place_names"] == ["Eva Bronce"]


def test_get_podiums_view_incomplete() -> None:
    """COMPLETED category without first_place_id → incomplete."""
    tournament = _create_tournament(name="Podios Incomplete")
    _create_category(
        tournament.id,
        name="Kata Ind",
        status=CategoryStatus.COMPLETED.value,
    )

    result = ResultsService.get_podiums_view(tournament.id)
    cards = result.get("categories", [])
    assert len(cards) == 1
    assert cards[0]["podium_status"] == "incomplete"


def test_get_podiums_view_unsupported_team() -> None:
    """COMPLETED team modality → unsupported_team."""
    tournament = _create_tournament(name="Podios Team")
    _create_category(
        tournament.id,
        name="Kata Team",
        status=CategoryStatus.COMPLETED.value,
        modality=Modality.KATA_TEAM.value,
    )

    result = ResultsService.get_podiums_view(tournament.id)
    cards = result.get("categories", [])
    assert len(cards) == 1
    assert cards[0]["podium_status"] == "unsupported_team"


def test_get_podiums_view_not_completed() -> None:
    """PENDING/IN_PROGRESS category → not_completed."""
    tournament = _create_tournament(name="Podios Not Done")
    _create_category(
        tournament.id,
        name="Kumite Pend",
        status=CategoryStatus.PENDING.value,
    )

    result = ResultsService.get_podiums_view(tournament.id)
    cards = result.get("categories", [])
    assert len(cards) == 1
    assert cards[0]["podium_status"] == "not_completed"


def test_get_podiums_view_defensive_third_place() -> None:
    """third_place_ids=None or '' does not crash."""
    tournament = _create_tournament(name="Podios 3rd")
    a1 = _create_athlete_for_test(name="First")
    a2 = _create_athlete_for_test(name="Second")
    category = _create_category(
        tournament.id,
        name="Kata Ind 3rd",
        status=CategoryStatus.COMPLETED.value,
    )
    with rx.session() as session:
        db_cat = session.get(TournamentCategory, category.id)
        assert db_cat is not None
        db_cat.first_place_id = a1.id
        db_cat.second_place_id = a2.id
        # third_place_ids left as None intentionally
        session.add(db_cat)
        session.commit()

    # Should not crash — card is still "available" with first/second present
    result = ResultsService.get_podiums_view(tournament.id)
    cards = result.get("categories", [])
    assert len(cards) == 1
    assert cards[0]["podium_status"] == "available"


def test_get_statistics_view_counts() -> None:
    """Aggregates total/completed counts and breakdowns."""
    tournament = _create_tournament(name="Stats Test")
    cat1 = _create_category(
        tournament.id,
        name="Kata Sr",
        status=CategoryStatus.COMPLETED.value,
        modality=Modality.KATA_INDIVIDUAL.value,
        competition_system=CompetitionSystem.ROUND_ROBIN.value,
    )
    cat2 = _create_category(
        tournament.id,
        name="Kumite Sr",
        status=CategoryStatus.COMPLETED.value,
        modality=Modality.KUMITE_INDIVIDUAL.value,
        competition_system=CompetitionSystem.ELIMINATION.value,
    )
    cat3 = _create_category(
        tournament.id,
        name="Kata Jr",
        status=CategoryStatus.PENDING.value,
        modality=Modality.KATA_INDIVIDUAL.value,
        competition_system=CompetitionSystem.ROUND_ROBIN.value,
    )
    _create_match(
        cat1.id, status=MatchStatus.COMPLETED.value, tournament_id=tournament.id
    )
    _create_match(
        cat1.id, status=MatchStatus.COMPLETED.value, tournament_id=tournament.id
    )
    _create_match(
        cat2.id, status=MatchStatus.PENDING.value, tournament_id=tournament.id
    )
    _create_match(
        cat3.id, status=MatchStatus.PENDING.value, tournament_id=tournament.id
    )

    result = ResultsService.get_statistics_view(tournament.id)

    assert result["total_categories"] == 3
    assert result["completed_categories"] == 2
    assert result["total_matches"] == 4
    assert result["completed_matches"] == 2

    by_mod = result.get("by_modality", {})
    assert by_mod["KATA_INDIVIDUAL"]["total_categories"] == 2
    assert by_mod["KATA_INDIVIDUAL"]["completed_categories"] == 1
    assert by_mod["KUMITE_INDIVIDUAL"]["total_categories"] == 1
    assert by_mod["KUMITE_INDIVIDUAL"]["completed_categories"] == 1

    by_sys = result.get("by_system", {})
    assert by_sys["ROUND_ROBIN"]["total_categories"] == 2
    assert by_sys["ELIMINATION"]["total_categories"] == 1

    by_ms = result.get("by_match_status", {})
    assert by_ms["COMPLETED"] == 2
    assert by_ms["PENDING"] == 2


def test_get_statistics_view_aggregates_through_category_ids() -> None:
    """Matches with tournament_id=None but valid category_id are counted."""
    tournament = _create_tournament(name="Stats Cat ID")
    category = _create_category(
        tournament.id,
        name="Kumite NoTournID",
        status=CategoryStatus.COMPLETED.value,
    )
    _create_match(
        category.id, status=MatchStatus.COMPLETED.value, tournament_id=None
    )

    result = ResultsService.get_statistics_view(tournament.id)

    assert result["total_matches"] == 1
    assert result["completed_matches"] == 1


# ==============================================================================
# Triangulation — edge cases for podiums/statistics
# ==============================================================================


def test_get_podiums_view_empty_tournament() -> None:
    """Tournament with no categories returns empty cards list."""
    tournament = _create_tournament(name="Podios Empty")
    result = ResultsService.get_podiums_view(tournament.id)
    assert result["categories"] == []


def test_get_podiums_view_kumite_team_unsupported() -> None:
    """KUMITE_TEAM also triggers unsupported_team status."""
    tournament = _create_tournament(name="Podios Kumite Team")
    _create_category(
        tournament.id,
        name="Kumite Team",
        status=CategoryStatus.COMPLETED.value,
        modality=Modality.KUMITE_TEAM.value,
    )
    result = ResultsService.get_podiums_view(tournament.id)
    assert result["categories"][0]["podium_status"] == "unsupported_team"


def test_get_podiums_view_in_progress_not_completed() -> None:
    """IN_PROGRESS (not just PENDING) → not_completed."""
    tournament = _create_tournament(name="Podios InProg")
    _create_category(
        tournament.id,
        name="Kumite InProg",
        status=CategoryStatus.IN_PROGRESS.value,
    )
    result = ResultsService.get_podiums_view(tournament.id)
    assert result["categories"][0]["podium_status"] == "not_completed"


def test_get_statistics_view_empty_tournament() -> None:
    """Tournament with no categories returns zero counts."""
    tournament = _create_tournament(name="Stats Empty")
    result = ResultsService.get_statistics_view(tournament.id)
    assert result["total_categories"] == 0
    assert result["completed_categories"] == 0
    assert result["total_matches"] == 0
    assert result["completed_matches"] == 0
    assert result["by_modality"] == {}
    assert result["by_system"] == {}
    assert result["by_match_status"] == {}


def test_get_statistics_view_invalid_id_raises_value_error() -> None:
    """Invalid tournament id raises ValueError."""
    with pytest.raises(ValueError):
        ResultsService.get_statistics_view(0)
    with pytest.raises(ValueError):
        ResultsService.get_statistics_view(-5)
    with pytest.raises(ValueError):
        ResultsService.get_statistics_view(999999)


def test_get_podiums_view_invalid_id_raises_value_error() -> None:
    """Invalid tournament id raises ValueError."""
    with pytest.raises(ValueError):
        ResultsService.get_podiums_view(0)
    with pytest.raises(ValueError):
        ResultsService.get_podiums_view(-5)
    with pytest.raises(ValueError):
        ResultsService.get_podiums_view(999999)
