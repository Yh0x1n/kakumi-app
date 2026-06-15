"""Behavioral tests for bracket generation service."""

import datetime

import pytest
import reflex as rx
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.tournament_model import (
    BracketSide,
    CategoryGender,
    CompetitionSystem,
    Match,
    MatchStatus,
    MatchType,
    Modality,
    Tournament,
    TournamentCategory,
    TournamentStatus,
)
from kakumi_app.services.bracket_service import BracketService
from kakumi_app.services.exceptions import ValidationError


def _create_tournament(name: str = "Bracket Service Tournament") -> Tournament:
    with rx.session() as session:
        tournament = Tournament(
            name=name,
            venue="Dojo Central",
            start_date=datetime.date(2026, 6, 1),
            end_date=datetime.date(2026, 6, 2),
            status=TournamentStatus.VERIFICACION.value,
        )
        session.add(tournament)
        session.commit()
        session.refresh(tournament)
        return tournament


def _create_category(
    tournament_id: int,
    *,
    name: str,
    modality: Modality,
    system: CompetitionSystem,
) -> TournamentCategory:
    with rx.session() as session:
        category = TournamentCategory(
            name=name,
            modality=modality.value,
            gender=CategoryGender.MIXED.value,
            min_age=10,
            max_age=35,
            competition_system=system.value,
            bracket_size=8,
            tournament_id=tournament_id,
        )
        session.add(category)
        session.commit()
        session.refresh(category)
        return category


def _create_athletes(
    *,
    category_id: int,
    modality: Modality,
    count: int,
    prefix: str,
) -> list[Athlete]:
    athletes: list[Athlete] = []
    with rx.session() as session:
        for index in range(count):
            athlete = Athlete(
                name=f"{prefix} Athlete {index}",
                age=19,
                gender="MALE",
                email=f"{prefix.lower()}-{index}@test.local",
                weight_kg=70.0,
                belt_rank="Negro",
                dojo="Dojo Test",
                nationality="ARG",
                license_number=f"{prefix.upper()}-{index}",
                is_active=True,
            )
            session.add(athlete)
            athletes.append(athlete)

        session.commit()

        for athlete in athletes:
            session.refresh(athlete)

    return athletes


def _persisted_matches(category_id: int) -> list[Match]:
    with rx.session() as session:
        return session.exec(
            select(Match)
            .where(Match.category_id == category_id)
            .order_by(Match.round, Match.position, Match.id)
        ).all()


def _round_matches(matches: list[Match], round_number: int) -> list[Match]:
    return [match for match in matches if match.round == round_number]


def test_generate_elimination_for_eight_participants_creates_full_tree() -> None:
    tournament = _create_tournament("Bracket Elimination Eight")
    category = _create_category(
        tournament.id,
        name="Kata Senior",
        modality=Modality.KATA_INDIVIDUAL,
        system=CompetitionSystem.ELIMINATION,
    )
    _create_athletes(
        category_id=category.id,
        modality=Modality.KATA_INDIVIDUAL,
        count=8,
        prefix="kata-eight",
    )

    result = BracketService(
        tournament_id=tournament.id,
        category_id=category.id,
    ).generate_bracket()

    matches = _persisted_matches(category.id)

    assert result["status"] == "generated"
    assert result["match_count"] == 7
    assert len(matches) == 7
    assert {match.round for match in matches} == {1, 2, 3}
    assert sum(match.match_type == MatchType.FINAL.value for match in matches) == 1
    assert all(match.ao_id is not None for match in matches if match.round == 1)


def test_generate_elimination_for_five_participants_creates_valid_byes() -> None:
    tournament = _create_tournament("Bracket Elimination Five")
    category = _create_category(
        tournament.id,
        name="Kumite Cadet",
        modality=Modality.KUMITE_INDIVIDUAL,
        system=CompetitionSystem.ELIMINATION,
    )
    athletes = _create_athletes(
        category_id=category.id,
        modality=Modality.KUMITE_INDIVIDUAL,
        count=5,
        prefix="kumite-five",
    )

    result = BracketService(
        tournament_id=tournament.id,
        category_id=category.id,
    ).generate_bracket()

    matches = _persisted_matches(category.id)
    bye_matches = [
        match for match in matches if match.round == 1 and match.ao_id is None
    ]
    participant_ids = {athlete.id for athlete in athletes}

    assert result["match_count"] == 7
    assert len(matches) == 7
    assert {match.round for match in matches} == {1, 2, 3}
    assert len(bye_matches) == 3
    assert all(match.status == MatchStatus.COMPLETED.value for match in bye_matches)
    assert all(match.winner_id == match.aka_id for match in bye_matches)
    assert {match.aka_id for match in bye_matches}.issubset(participant_ids)
    assert sum(match.match_type == MatchType.FINAL.value for match in matches) == 1


def test_elimination_persists_draw_through_first_round_matches() -> None:
    tournament = _create_tournament("Bracket Draw Persistence")
    category = _create_category(
        tournament.id,
        name="Kata Draw Order",
        modality=Modality.KATA_INDIVIDUAL,
        system=CompetitionSystem.ELIMINATION,
    )
    athletes = _create_athletes(
        category_id=category.id,
        modality=Modality.KATA_INDIVIDUAL,
        count=5,
        prefix="draw-order",
    )

    BracketService(
        tournament_id=tournament.id,
        category_id=category.id,
    ).generate_bracket()

    round_one_matches = _round_matches(_persisted_matches(category.id), 1)
    persisted_positions = [match.position for match in round_one_matches]
    persisted_ids = [
        participant_id
        for match in round_one_matches
        for participant_id in (match.aka_id, match.ao_id)
        if participant_id is not None
    ]

    assert persisted_positions == [1, 2, 3, 4]
    assert set(persisted_ids) == {athlete.id for athlete in athletes}
    assert len(persisted_ids) == len(athletes)


def test_generate_round_robin_for_four_participants_creates_unique_pairings() -> None:
    tournament = _create_tournament("Bracket Round Robin Four")
    category = _create_category(
        tournament.id,
        name="Kata League",
        modality=Modality.KATA_INDIVIDUAL,
        system=CompetitionSystem.ROUND_ROBIN,
    )
    athletes = _create_athletes(
        category_id=category.id,
        modality=Modality.KATA_INDIVIDUAL,
        count=4,
        prefix="rr-four",
    )

    result = BracketService(
        tournament_id=tournament.id,
        category_id=category.id,
    ).generate_bracket()

    matches = _persisted_matches(category.id)
    expected_pairs = len(athletes) * (len(athletes) - 1) // 2
    unique_pairs = {
        frozenset((match.aka_id, match.ao_id))
        for match in matches
        if match.aka_id is not None and match.ao_id is not None
    }

    assert result["match_count"] == 6
    assert len(matches) == expected_pairs
    assert len(unique_pairs) == expected_pairs
    assert all(match.aka_id != match.ao_id for match in matches)
    assert all(match.match_type == MatchType.ROUND_ROBIN.value for match in matches)


def test_regeneration_is_blocked_with_stable_error_code() -> None:
    tournament = _create_tournament("Bracket Regeneration Guard")
    category = _create_category(
        tournament.id,
        name="Regeneration Category",
        modality=Modality.KATA_INDIVIDUAL,
        system=CompetitionSystem.ELIMINATION,
    )
    _create_athletes(
        category_id=category.id,
        modality=Modality.KATA_INDIVIDUAL,
        count=4,
        prefix="regen",
    )

    service = BracketService(
        tournament_id=tournament.id,
        category_id=category.id,
    )
    service.generate_bracket()

    with pytest.raises(ValidationError) as exc_info:
        service.generate_bracket()

    assert exc_info.value.code == "BRACKET_ALREADY_EXISTS"


def test_unsupported_system_returns_stable_error_code() -> None:
    tournament = _create_tournament("Bracket Unsupported System")
    category = _create_category(
        tournament.id,
        name="Double Elimination Deferred",
        modality=Modality.KUMITE_INDIVIDUAL,
        system=CompetitionSystem.DOUBLE_ELIMINATION,
    )
    _create_athletes(
        category_id=category.id,
        modality=Modality.KUMITE_INDIVIDUAL,
        count=4,
        prefix="double-elim",
    )

    with pytest.raises(ValidationError) as exc_info:
        BracketService(
            tournament_id=tournament.id,
            category_id=category.id,
        ).generate_bracket()

    assert exc_info.value.code == "UNSUPPORTED_SYSTEM"


def test_insufficient_participants_returns_stable_error_code() -> None:
    tournament = _create_tournament("Bracket Insufficient Participants")
    category = _create_category(
        tournament.id,
        name="Too Small Category",
        modality=Modality.KATA_INDIVIDUAL,
        system=CompetitionSystem.ELIMINATION,
    )
    _create_athletes(
        category_id=category.id,
        modality=Modality.KATA_INDIVIDUAL,
        count=1,
        prefix="insufficient",
    )

    with pytest.raises(ValidationError) as exc_info:
        BracketService(
            tournament_id=tournament.id,
            category_id=category.id,
        ).generate_bracket()

    assert exc_info.value.code == "INSUFFICIENT_PARTICIPANTS"


def test_kumite_elimination_creates_no_bronze_match() -> None:
    tournament = _create_tournament("Bracket No Bronze")
    category = _create_category(
        tournament.id,
        name="Kumite Senior",
        modality=Modality.KUMITE_INDIVIDUAL,
        system=CompetitionSystem.ELIMINATION,
    )
    _create_athletes(
        category_id=category.id,
        modality=Modality.KUMITE_INDIVIDUAL,
        count=4,
        prefix="no-bronze",
    )

    BracketService(
        tournament_id=tournament.id,
        category_id=category.id,
    ).generate_bracket()

    matches = _persisted_matches(category.id)

    assert all(match.match_type != MatchType.BRONZE.value for match in matches)
    assert all(match.bracket_side == BracketSide.WINNERS.value for match in matches)
