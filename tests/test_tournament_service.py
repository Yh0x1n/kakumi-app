"""Strict-TDD coverage for tournament service bracket guard (INFORMAL skip)."""

from __future__ import annotations

import datetime

import pytest
import reflex as rx
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.tournament_model import (
    CategoryGender,
    CompetitionSystem,
    Match,
    Modality,
    Tournament,
    TournamentCategory,
    TournamentStatus,
)
from kakumi_app.services.tournament_service import TournamentService


def _make_tournament() -> Tournament:
    """Create a minimal tournament in VERIFICACION status."""
    with rx.session() as session:
        tournament = Tournament(
            name="Bracket Guard Test",
            venue="Dojo Test",
            start_date=datetime.date(2026, 7, 1),
            end_date=datetime.date(2026, 7, 2),
            status=TournamentStatus.VERIFICACION.value,
        )
        session.add(tournament)
        session.commit()
        session.refresh(tournament)
        return tournament


def _make_category(
    tournament_id: int,
    *,
    name: str,
    kata_flow_mode: str = "STANDARD",
) -> TournamentCategory:
    """Create a category with the given kata_flow_mode."""
    with rx.session() as session:
        category = TournamentCategory(
            name=name,
            modality=Modality.KATA_INDIVIDUAL.value,
            gender=CategoryGender.MIXED.value,
            min_age=10,
            max_age=99,
            competition_system=CompetitionSystem.ELIMINATION.value,
            bracket_size=8,
            tournament_id=tournament_id,
            judge_panel_size=3,
            kata_flow_mode=kata_flow_mode,
            kata_decision_rule="AVERAGE_WITH_DISCARD",
        )
        session.add(category)
        session.commit()
        session.refresh(category)
        return category


def _make_athletes(tournament_id: int, count: int = 8) -> None:
    """Create athletes that match MIXED gender and broad age range."""
    with rx.session() as session:
        for index in range(count):
            session.add(
                Athlete(
                    name=f"Bracket Athlete {index}",
                    age=20 + index,
                    gender="MALE",
                    email=f"bracket-{index}@test.local",
                    weight_kg=70.0,
                    belt_rank="Negro",
                    dojo="Dojo Test",
                    nationality="ARG",
                    license_number=f"BRACKET-{index}",
                    is_active=True,
                )
            )
        session.commit()


def _match_count(category_id: int) -> int:
    """Return number of Match rows for a given category."""
    with rx.session() as session:
        return len(
            session.exec(
                select(Match).where(Match.category_id == category_id)
            ).all()
        )


def test_bracket_guard_skips_informal() -> None:
    """_generate_brackets_for_tournament() skips INFORMAL categories."""
    tournament = _make_tournament()
    standard_cat = _make_category(tournament.id, name="Standard Kata")
    informal_cat = _make_category(
        tournament.id, name="Informal Kata", kata_flow_mode="INFORMAL"
    )
    _make_athletes(tournament.id, count=8)

    TournamentService._generate_brackets_for_tournament(tournament.id)

    assert _match_count(standard_cat.id) > 0, (
        "STANDARD category should have Match records"
    )
    assert _match_count(informal_cat.id) == 0, (
        "INFORMAL category should have zero Match records"
    )


def test_bracket_guard_standard_unaffected() -> None:
    """STANDARD categories still generate brackets normally."""
    tournament = _make_tournament()
    standard_cat = _make_category(tournament.id, name="Standard Only")
    _make_athletes(tournament.id, count=8)

    TournamentService._generate_brackets_for_tournament(tournament.id)

    match_count = _match_count(standard_cat.id)
    assert match_count > 0, "STANDARD category should generate Match records"
    assert match_count == 7, (
        "8-athlete elimination should produce 7 matches"
    )


def test_bracket_guard_mixed_tournament_skips_only_informal() -> None:
    """Mixed tournament: only INFORMAL skipped, both STANDARD get matches."""
    tournament = _make_tournament()
    std_kata = _make_category(tournament.id, name="Standard Kata")
    inf_kata = _make_category(
        tournament.id, name="Informal Kata", kata_flow_mode="INFORMAL"
    )
    std_kumite_cat = TournamentCategory(
        name="Standard Kumite",
        modality=Modality.KUMITE_INDIVIDUAL.value,
        gender=CategoryGender.MIXED.value,
        min_age=10,
        max_age=99,
        competition_system=CompetitionSystem.ELIMINATION.value,
        bracket_size=8,
        tournament_id=tournament.id,
        judge_panel_size=3,
    )
    with rx.session() as session:
        session.add(std_kumite_cat)
        session.commit()
        session.refresh(std_kumite_cat)

    _make_athletes(tournament.id, count=8)

    TournamentService._generate_brackets_for_tournament(tournament.id)

    assert _match_count(std_kata.id) > 0, "Standard kata should have matches"
    assert _match_count(inf_kata.id) == 0, "INFORMAL kata should have zero matches"
    assert _match_count(std_kumite_cat.id) > 0, "Standard kumite should have matches"


def test_bracket_guard_no_informal_no_change() -> None:
    """Tournament with zero INFORMAL categories — all generate as before."""
    tournament = _make_tournament()
    cat_a = _make_category(tournament.id, name="Kata A")
    cat_b = _make_category(tournament.id, name="Kata B")
    _make_athletes(tournament.id, count=8)

    TournamentService._generate_brackets_for_tournament(tournament.id)

    assert _match_count(cat_a.id) == 7
    assert _match_count(cat_b.id) == 7
