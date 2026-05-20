"""Tests for informal Kata round-robin service and finalize flow."""

from __future__ import annotations

import pytest
import reflex as rx

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.tournament_model import MatchType
from kakumi_app.models.tournament_model import (
    CategoryGender,
    CategoryStatus,
    CompetitionSystem,
    Modality,
    TournamentCategory,
)


def _create_informal_category(tournament_id: int) -> TournamentCategory:
    """Create informal kata category for ranking scenarios."""
    with rx.session() as session:
        category = TournamentCategory(
            name="Kata Informal Senior",
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
    """Create athlete bound to kata category roster."""
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


def _create_match(category_id: int, aka_id: int, ao_id: int) -> int:
    """Create helper match for standings/tie-break criteria."""
    from kakumi_app.models.tournament_model import Match

    with rx.session() as session:
        match = Match(
            round=1,
            match_number=1,
            position=0,
            match_type=MatchType.ROUND_ROBIN.value,
            category_id=category_id,
            aka_id=aka_id,
            ao_id=ao_id,
        )
        session.add(match)
        session.commit()
        session.refresh(match)
        return int(match.id)


def test_save_performance_calculates_final_score_with_drop_high_low(
    sample_tournament,
) -> None:
    """5-judge panel score drops high/low and averages 3 middle scores."""
    from kakumi_app.services.kata_informal_service import KataInformalService

    category = _create_informal_category(sample_tournament.id)
    athlete = _create_athlete("Informal A", "informal-a@test.local", category.id)

    performance = KataInformalService.save_performance(
        category_id=category.id,
        athlete_id=athlete.id,
        judge_scores=[9.0, 8.0, 8.5, 8.8, 7.0],
    )

    # After dropping high/low, final score = SUM of remaining three scores
    assert performance.final_score == pytest.approx(8.0 + 8.5 + 8.8)
    assert performance.highest_score == pytest.approx(9.0)
    assert performance.lowest_score == pytest.approx(7.0)


def test_rankings_apply_tie_break_by_highest_individual_score(
    sample_tournament,
) -> None:
    """Tie by final score resolves by highest single judge score (spec 5.2.1)."""
    from kakumi_app.services.kata_informal_service import KataInformalService

    category = _create_informal_category(sample_tournament.id)
    athlete_a = _create_athlete("Tie A", "tie-a@test.local", category.id)
    athlete_b = _create_athlete("Tie B", "tie-b@test.local", category.id)

    KataInformalService.save_performance(
        category_id=category.id,
        athlete_id=athlete_a.id,
        judge_scores=[8.9, 8.4, 8.4, 8.4, 7.9],
    )
    KataInformalService.save_performance(
        category_id=category.id,
        athlete_id=athlete_b.id,
        judge_scores=[8.8, 8.4, 8.4, 8.4, 8.0],
    )

    standings = KataInformalService.rank_category(category.id)
    assert standings[0]["athlete_id"] == athlete_a.id
    assert standings[1]["athlete_id"] == athlete_b.id
    assert standings[0]["needs_extra_kata"] is False


def test_rankings_flag_needs_extra_kata_when_tie_unresolved(sample_tournament) -> None:
    """Unresolved tie marks both athletes as requiring extra kata."""
    from kakumi_app.services.kata_informal_service import KataInformalService

    category = _create_informal_category(sample_tournament.id)
    athlete_a = _create_athlete("Extra A", "extra-a@test.local", category.id)
    athlete_b = _create_athlete("Extra B", "extra-b@test.local", category.id)

    KataInformalService.save_performance(
        category_id=category.id,
        athlete_id=athlete_a.id,
        judge_scores=[8.5, 8.0, 7.5, 8.0, 6.0],
    )
    KataInformalService.save_performance(
        category_id=category.id,
        athlete_id=athlete_b.id,
        judge_scores=[8.5, 8.0, 7.5, 8.0, 6.0],
    )

    standings = KataInformalService.rank_category(category.id)
    tied = [
        row for row in standings if row["final_score"] == standings[0]["final_score"]
    ]
    assert tied[0]["needs_extra_kata"] is True
    assert tied[1]["needs_extra_kata"] is True


def test_rankings_apply_criterion_1_victory_points_first(sample_tournament) -> None:
    """Criterion 1: more encounter points outrank better panel score."""
    from kakumi_app.services.kata_informal_service import KataInformalService
    from kakumi_app.services.kata_scoring_service import KataScoringService

    category = _create_informal_category(sample_tournament.id)
    athlete_a = _create_athlete("VP A", "vp-a@test.local", category.id)
    athlete_b = _create_athlete("VP B", "vp-b@test.local", category.id)

    match_id = _create_match(category.id, athlete_a.id, athlete_b.id)
    KataScoringService.assign_victory_points(
        match_id=match_id,
        winner_participant="AKA",
        aka_votes=3,
        ao_votes=2,
    )

    KataInformalService.save_performance(
        category_id=category.id,
        athlete_id=athlete_a.id,
        judge_scores=[8.1, 8.0, 8.0, 8.0, 7.9],
    )
    KataInformalService.save_performance(
        category_id=category.id,
        athlete_id=athlete_b.id,
        judge_scores=[9.1, 9.0, 9.0, 9.0, 8.9],
    )

    standings = KataInformalService.rank_category(category.id)
    assert standings[0]["athlete_id"] == athlete_a.id
    assert standings[0]["victory_points"] == 3
    assert standings[1]["victory_points"] == 0


def test_rankings_apply_criterion_2_head_to_head_before_criterion_3(
    sample_tournament,
) -> None:
    """Criterion 2: encounter winner breaks tie before criterion 3."""
    from kakumi_app.services.kata_informal_service import KataInformalService
    from kakumi_app.services.kata_scoring_service import KataScoringService

    category = _create_informal_category(sample_tournament.id)
    athlete_a = _create_athlete("H2H A", "h2h-a@test.local", category.id)
    athlete_b = _create_athlete("H2H B", "h2h-b@test.local", category.id)
    athlete_d = _create_athlete("H2H D", "h2h-d@test.local", category.id)

    match_ab = _create_match(category.id, athlete_a.id, athlete_b.id)
    match_bd = _create_match(category.id, athlete_b.id, athlete_d.id)
    KataScoringService.assign_victory_points(
        match_id=match_ab,
        winner_participant="AKA",
        aka_votes=3,
        ao_votes=2,
    )
    KataScoringService.assign_victory_points(
        match_id=match_bd,
        winner_participant="AKA",
        aka_votes=3,
        ao_votes=2,
    )

    KataInformalService.save_performance(
        category_id=category.id,
        athlete_id=athlete_a.id,
        judge_scores=[8.6, 8.0, 8.0, 8.0, 7.4],
    )
    KataInformalService.save_performance(
        category_id=category.id,
        athlete_id=athlete_b.id,
        judge_scores=[9.5, 8.0, 8.0, 8.0, 6.5],
    )

    standings = KataInformalService.rank_category(category.id)
    assert standings[0]["athlete_id"] == athlete_a.id
    assert standings[1]["athlete_id"] == athlete_b.id
    assert standings[0]["victory_points"] == 3
    assert standings[1]["victory_points"] == 3


def test_finalize_category_requires_full_roster_performances(sample_tournament) -> None:
    """Finalization fails until every roster athlete has one performance."""
    from kakumi_app.services.kata_informal_service import KataInformalService

    category = _create_informal_category(sample_tournament.id)
    athlete_a = _create_athlete("Guard A", "guard-a@test.local", category.id)
    _create_athlete("Guard B", "guard-b@test.local", category.id)

    KataInformalService.save_performance(
        category_id=category.id,
        athlete_id=athlete_a.id,
        judge_scores=[8.0, 8.0, 8.0, 8.0, 8.0],
    )

    with pytest.raises(ValueError, match="sin puntuar"):
        KataInformalService.finalize_category(category.id)


def test_finalize_category_sets_podium_without_matches(sample_tournament) -> None:
    """Informal finalization writes podium directly with no pairwise matches."""
    from kakumi_app.services.kata_informal_service import KataInformalService

    category = _create_informal_category(sample_tournament.id)
    athlete_1 = _create_athlete("Podium 1", "podium-1@test.local", category.id)
    athlete_2 = _create_athlete("Podium 2", "podium-2@test.local", category.id)
    athlete_3 = _create_athlete("Podium 3", "podium-3@test.local", category.id)

    KataInformalService.save_performance(
        category_id=category.id,
        athlete_id=athlete_1.id,
        judge_scores=[9.0, 8.8, 8.7, 8.6, 8.5],
    )
    KataInformalService.save_performance(
        category_id=category.id,
        athlete_id=athlete_2.id,
        judge_scores=[8.6, 8.5, 8.4, 8.3, 8.2],
    )
    KataInformalService.save_performance(
        category_id=category.id,
        athlete_id=athlete_3.id,
        judge_scores=[8.0, 7.9, 7.8, 7.7, 7.6],
    )

    finalized = KataInformalService.finalize_category(category.id)

    assert finalized.status == CategoryStatus.COMPLETED.value
    assert finalized.first_place_id == athlete_1.id
    assert finalized.second_place_id == athlete_2.id
    assert str(athlete_3.id) in str(finalized.third_place_ids)
