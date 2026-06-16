"""
Behavioral and regression tests for bracket generation service.

Merged from:
  - test_bracket_service.py (backbone, classes TestElimination, TestRoundRobin)
  - test_bracket_service_critical_fixes.py (class TestCriticalFixes)
  - test_winner_propagation.py (class TestWinnerPropagation)
"""

from __future__ import annotations

import datetime
import importlib
from pathlib import Path

import pytest
import reflex as rx
import sqlalchemy as sa
from alembic import command
from sqlmodel import SQLModel, Session, create_engine, select

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
from kakumi_app.services.bracket_service import (
    _build_elimination,
    generate_bracket,
    propagate_winner,
)
from kakumi_app.services.exceptions import ValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]


# =============================================================================
# Shared helpers
# =============================================================================


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


def _make_tournament() -> Tournament:
    from kakumi_app.models.tournament_model import Tournament, TournamentStatus

    return Tournament(
        name="Critical Fix Tournament",
        venue="Dojo Central",
        start_date=datetime.date(2026, 4, 27),
        end_date=datetime.date(2026, 4, 28),
        status=TournamentStatus.VERIFICACION.value,
    )


def _make_category(tournament_id: int) -> TournamentCategory:
    from kakumi_app.models.tournament_model import (
        CategoryGender,
        CompetitionSystem,
        Modality,
        TournamentCategory,
    )

    return TournamentCategory(
        name="U12 Kata",
        modality=Modality.KATA_INDIVIDUAL.value,
        gender=CategoryGender.MIXED.value,
        min_age=8,
        max_age=12,
        competition_system=CompetitionSystem.ELIMINATION.value,
        bracket_size=8,
        tournament_id=tournament_id,
    )


def _add_category_athletes(session: Session, category_id: int, count: int = 2) -> None:
    from kakumi_app.models.athlete_model import Athlete

    for index in range(count):
        session.add(
            Athlete(
                name=f"Critical Athlete {category_id}-{index}",
                age=10,
                gender="MALE",
                email=f"critical-{category_id}-{index}@test.local",
                weight_kg=42.0,
                belt_rank="Negro",
                dojo="Dojo Central",
                nationality="ARG",
                license_number=f"CRIT-{category_id}-{index}",
                is_active=True,
            )
        )


# =============================================================================
# Elimination bracket tests — from test_bracket_service.py
# =============================================================================


class TestElimination:
    """Elimination bracket generation, validation, and edge cases."""

    @staticmethod
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

        result = generate_bracket(
            tournament_id=tournament.id,
            category_id=category.id,
        )

        matches = _persisted_matches(category.id)

        assert result["status"] == "generated"
        assert result["match_count"] == 7
        assert len(matches) == 7
        assert {match.round for match in matches} == {1, 2, 3}
        assert sum(match.match_type == MatchType.FINAL.value for match in matches) == 1
        assert all(match.ao_id is not None for match in matches if match.round == 1)

    @staticmethod
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

        result = generate_bracket(
            tournament_id=tournament.id,
            category_id=category.id,
        )

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

    @staticmethod
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

        generate_bracket(
            tournament_id=tournament.id,
            category_id=category.id,
        )

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

    @staticmethod
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

        generate_bracket(
            tournament_id=tournament.id,
            category_id=category.id,
        )

        with pytest.raises(ValidationError) as exc_info:
            generate_bracket(
                tournament_id=tournament.id,
                category_id=category.id,
            )

        assert exc_info.value.code == "BRACKET_ALREADY_EXISTS"

    @staticmethod
    def test_unsupported_system_returns_stable_error_code() -> None:
        tournament = _create_tournament("Bracket Unsupported System")
        with rx.session() as session:
            category = TournamentCategory(
                name="Unknown System",
                modality=Modality.KUMITE_INDIVIDUAL.value,
                gender=CategoryGender.MIXED.value,
                min_age=10,
                max_age=35,
                competition_system="DOUBLE_ELIMINATION",
                bracket_size=8,
                tournament_id=tournament.id,
            )
            session.add(category)
            session.commit()
            session.refresh(category)
        _create_athletes(
            category_id=category.id,
            modality=Modality.KUMITE_INDIVIDUAL,
            count=4,
            prefix="double-elim",
        )

        with pytest.raises(ValidationError) as exc_info:
            generate_bracket(
                tournament_id=tournament.id,
                category_id=category.id,
            )

        assert exc_info.value.code == "UNSUPPORTED_SYSTEM"

    @staticmethod
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
            generate_bracket(
                tournament_id=tournament.id,
                category_id=category.id,
            )

        assert exc_info.value.code == "INSUFFICIENT_PARTICIPANTS"

    @staticmethod
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

        generate_bracket(
            tournament_id=tournament.id,
            category_id=category.id,
        )

        matches = _persisted_matches(category.id)

        assert all(match.match_type != MatchType.BRONZE.value for match in matches)
        assert all(match.bracket_side == BracketSide.WINNERS.value for match in matches)


# =============================================================================
# Round-robin bracket tests — from test_bracket_service.py
# =============================================================================


class TestRoundRobin:
    """Round-robin bracket generation."""

    @staticmethod
    def test_generate_round_robin_for_four_participants_creates_unique_pairings() -> (
        None
    ):
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

        result = generate_bracket(
            tournament_id=tournament.id,
            category_id=category.id,
        )

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


# =============================================================================
# Winner propagation tests — from test_winner_propagation.py
# =============================================================================


class TestWinnerPropagation:
    """Winner propagation in elimination brackets."""

    @staticmethod
    def _create_tournament(name: str = "Winner Propagation Tournament") -> Tournament:
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

    @staticmethod
    def _create_category(tournament_id: int) -> TournamentCategory:
        with rx.session() as session:
            category = TournamentCategory(
                name="Winner Propagation Category",
                modality=Modality.KATA_INDIVIDUAL.value,
                gender=CategoryGender.MIXED.value,
                min_age=10,
                max_age=35,
                competition_system=CompetitionSystem.ELIMINATION.value,
                bracket_size=4,
                tournament_id=tournament_id,
            )
            session.add(category)
            session.commit()
            session.refresh(category)
            return category

    @staticmethod
    def _create_athletes(count: int) -> list[Athlete]:
        athletes: list[Athlete] = []
        with rx.session() as session:
            for index in range(count):
                athlete = Athlete(
                    name=f"Prop Athlete {index}",
                    age=20,
                    gender="MALE",
                    email=f"prop-{index}@test.local",
                    weight_kg=70.0,
                    belt_rank="Negro",
                    dojo="Dojo Test",
                    nationality="ARG",
                    license_number=f"PROP-{index}",
                    is_active=True,
                )
                session.add(athlete)
                athletes.append(athlete)

            session.commit()
            for athlete in athletes:
                session.refresh(athlete)

        return athletes

    @staticmethod
    def test_propagate_odd_position_winner_to_next_aka() -> None:
        """Winner from odd-position match (pos=1) fills aka_id in next round."""
        tournament = TestWinnerPropagation._create_tournament()
        category = TestWinnerPropagation._create_category(tournament.id)
        athletes = TestWinnerPropagation._create_athletes(4)

        matches = _build_elimination(
            [a.id for a in athletes],
            tournament_id=tournament.id,
            category_id=category.id,
            is_team=False,
        )

        with rx.session() as session:
            session.add_all(matches)
            session.commit()
            for m in matches:
                session.refresh(m)

            semi = session.exec(
                select(Match).where(
                    Match.category_id == category.id,
                    Match.round == 1,
                    Match.position == 1,
                )
            ).first()
            assert semi is not None

            semi.winner_id = athletes[0].id
            session.add(semi)
            session.commit()

            propagate_winner(session, semi)
            session.commit()

            final = session.exec(
                select(Match).where(
                    Match.category_id == category.id,
                    Match.round == 2,
                    Match.position == 1,
                )
            ).first()
            assert final is not None
            assert final.aka_id == athletes[0].id
            assert final.ao_id is None

    @staticmethod
    def test_propagate_even_position_winner_to_next_ao() -> None:
        """Winner from even-position match (pos=2) fills ao_id in next round."""
        tournament = TestWinnerPropagation._create_tournament()
        category = TestWinnerPropagation._create_category(tournament.id)
        athletes = TestWinnerPropagation._create_athletes(4)

        matches = _build_elimination(
            [a.id for a in athletes],
            tournament_id=tournament.id,
            category_id=category.id,
            is_team=False,
        )

        with rx.session() as session:
            session.add_all(matches)
            session.commit()
            for m in matches:
                session.refresh(m)

            semi = session.exec(
                select(Match).where(
                    Match.category_id == category.id,
                    Match.round == 1,
                    Match.position == 2,
                )
            ).first()
            assert semi is not None

            semi.winner_id = athletes[1].id
            session.add(semi)
            session.commit()

            propagate_winner(session, semi)
            session.commit()

            final = session.exec(
                select(Match).where(
                    Match.category_id == category.id,
                    Match.round == 2,
                    Match.position == 1,
                )
            ).first()
            assert final is not None
            assert final.ao_id == athletes[1].id
            assert final.aka_id is None

    @staticmethod
    def test_propagate_both_sides_fill_final_correctly() -> None:
        """Both semis propagate — both aka_id and ao_id set in final."""
        tournament = TestWinnerPropagation._create_tournament()
        category = TestWinnerPropagation._create_category(tournament.id)
        athletes = TestWinnerPropagation._create_athletes(4)

        matches = _build_elimination(
            [a.id for a in athletes],
            tournament_id=tournament.id,
            category_id=category.id,
            is_team=False,
        )

        with rx.session() as session:
            session.add_all(matches)
            session.commit()
            for m in matches:
                session.refresh(m)

            semi1 = session.exec(
                select(Match).where(
                    Match.category_id == category.id,
                    Match.round == 1,
                    Match.position == 1,
                )
            ).first()
            semi2 = session.exec(
                select(Match).where(
                    Match.category_id == category.id,
                    Match.round == 1,
                    Match.position == 2,
                )
            ).first()
            assert semi1 is not None
            assert semi2 is not None

            semi1.winner_id = athletes[0].id
            semi2.winner_id = athletes[2].id
            session.add(semi1)
            session.add(semi2)
            session.commit()

            propagate_winner(session, semi1)
            propagate_winner(session, semi2)
            session.commit()

            final = session.exec(
                select(Match).where(
                    Match.category_id == category.id,
                    Match.round == 2,
                    Match.position == 1,
                )
            ).first()
            assert final is not None
            assert final.aka_id == athletes[0].id
            assert final.ao_id == athletes[2].id

    @staticmethod
    def test_propagate_idempotent_when_slot_already_filled() -> None:
        """Second call does not overwrite a slot that is already filled."""
        tournament = TestWinnerPropagation._create_tournament()
        category = TestWinnerPropagation._create_category(tournament.id)
        athletes = TestWinnerPropagation._create_athletes(4)

        matches = _build_elimination(
            [a.id for a in athletes],
            tournament_id=tournament.id,
            category_id=category.id,
            is_team=False,
        )

        with rx.session() as session:
            session.add_all(matches)
            session.commit()
            for m in matches:
                session.refresh(m)

            semi = session.exec(
                select(Match).where(
                    Match.category_id == category.id,
                    Match.round == 1,
                    Match.position == 1,
                )
            ).first()
            assert semi is not None

            final = session.exec(
                select(Match).where(
                    Match.category_id == category.id,
                    Match.round == 2,
                    Match.position == 1,
                )
            ).first()
            assert final is not None
            final.aka_id = athletes[3].id  # pre-fill with different athlete
            session.add(final)
            session.commit()

            semi.winner_id = athletes[0].id
            session.add(semi)
            session.commit()

            propagate_winner(session, semi)
            session.commit()

            # Slot must keep original value, NOT the new winner
            assert final.aka_id == athletes[3].id

    @staticmethod
    def test_propagate_no_winner_id_does_nothing() -> None:
        """Match with winner_id=None does not propagate."""
        tournament = TestWinnerPropagation._create_tournament()
        category = TestWinnerPropagation._create_category(tournament.id)
        athletes = TestWinnerPropagation._create_athletes(4)

        matches = _build_elimination(
            [a.id for a in athletes],
            tournament_id=tournament.id,
            category_id=category.id,
            is_team=False,
        )

        with rx.session() as session:
            session.add_all(matches)
            session.commit()
            for m in matches:
                session.refresh(m)

            semi = session.exec(
                select(Match).where(
                    Match.category_id == category.id,
                    Match.round == 1,
                    Match.position == 1,
                )
            ).first()
            assert semi is not None
            assert semi.winner_id is None  # no winner yet

            propagate_winner(session, semi)
            session.commit()

            final = session.exec(
                select(Match).where(
                    Match.category_id == category.id,
                    Match.round == 2,
                    Match.position == 1,
                )
            ).first()
            assert final is not None
            assert final.aka_id is None
            assert final.ao_id is None

    @staticmethod
    def test_propagate_on_8_participant_bracket() -> None:
        """Verify positional math on a deeper bracket (3 rounds)."""
        tournament = TestWinnerPropagation._create_tournament("8 Participant Bracket")
        category = TestWinnerPropagation._create_category(tournament.id)
        athletes = TestWinnerPropagation._create_athletes(8)

        matches = _build_elimination(
            [a.id for a in athletes],
            tournament_id=tournament.id,
            category_id=category.id,
            is_team=False,
        )

        with rx.session() as session:
            session.add_all(matches)
            session.commit()
            for m in matches:
                session.refresh(m)

            # Set winners for all round-1 matches
            for pos in range(1, 5):
                semi = session.exec(
                    select(Match).where(
                        Match.category_id == category.id,
                        Match.round == 1,
                        Match.position == pos,
                    )
                ).first()
                assert semi is not None
                semi.winner_id = athletes[pos - 1].id
                session.add(semi)
            session.commit()

            # Propagate all round-1 winners
            for pos in range(1, 5):
                semi = session.exec(
                    select(Match).where(
                        Match.category_id == category.id,
                        Match.round == 1,
                        Match.position == pos,
                    )
                ).first()
                propagate_winner(session, semi)
            session.commit()

            # Round 2: position 1 should have aka=athlete[0], ao=athlete[1]
            r2p1 = session.exec(
                select(Match).where(
                    Match.category_id == category.id,
                    Match.round == 2,
                    Match.position == 1,
                )
            ).first()
            assert r2p1 is not None
            assert r2p1.aka_id == athletes[0].id
            assert r2p1.ao_id == athletes[1].id

            # Round 2: position 2 should have aka=athlete[2], ao=athlete[3]
            r2p2 = session.exec(
                select(Match).where(
                    Match.category_id == category.id,
                    Match.round == 2,
                    Match.position == 2,
                )
            ).first()
            assert r2p2 is not None
            assert r2p2.aka_id == athletes[2].id
            assert r2p2.ao_id == athletes[3].id

            # Now propagate round-2 winners to the final
            for pos in range(1, 3):
                semi = session.exec(
                    select(Match).where(
                        Match.category_id == category.id,
                        Match.round == 2,
                        Match.position == pos,
                    )
                ).first()
                semi.winner_id = athletes[pos - 1].id
                session.add(semi)
            session.commit()

            for pos in range(1, 3):
                semi = session.exec(
                    select(Match).where(
                        Match.category_id == category.id,
                        Match.round == 2,
                        Match.position == pos,
                    )
                ).first()
                propagate_winner(session, semi)
            session.commit()

            final = session.exec(
                select(Match).where(
                    Match.category_id == category.id,
                    Match.round == 3,
                    Match.position == 1,
                )
            ).first()
            assert final is not None
            assert final.aka_id == athletes[0].id
            assert final.ao_id == athletes[1].id


# =============================================================================
# Critical fixes regression tests — from test_bracket_service_critical_fixes.py
# =============================================================================


class TestCriticalFixes:
    """Critical regression coverage for bracket service foundations."""

    @staticmethod
    def test_no_sqlalchemy_mapper_conflict() -> None:
        """Importing models should register one usable Match mapper."""
        models = importlib.import_module("kakumi_app.models")
        tournament_models = importlib.import_module(
            "kakumi_app.models.tournament_model"
        )

        assert models.Match is tournament_models.Match
        assert models.Match.__tablename__ == "matches"

    @staticmethod
    def test_query_match_returns_single_type() -> None:
        """Querying Match should return the unified mapped type."""
        from kakumi_app.models.tournament_model import Match

        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            tournament = _make_tournament()
            session.add(tournament)
            session.flush()

            category = _make_category(tournament.id)
            session.add(category)
            session.flush()

            match = Match(
                tournament_id=tournament.id,
                category_id=category.id,
                round=1,
                position=1,
                match_type="ELIMINATION",
            )
            session.add(match)
            session.commit()

            result = session.query(Match).filter(Match.id == match.id).first()

        assert result is not None
        assert isinstance(result, Match)
        assert result.__class__ is Match

    @staticmethod
    def test_bracket_service_guard_existing_matches() -> None:
        """generate_bracket() must re-check and block regeneration."""
        from kakumi_app.models.tournament_model import Match

        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            tournament = _make_tournament()
            session.add(tournament)
            session.flush()
            tournament_id = tournament.id

            category = _make_category(tournament_id)
            session.add(category)
            session.flush()
            category_id = category.id
            _add_category_athletes(session, category_id)
            session.flush()

            generate_bracket(
                tournament_id=tournament_id,
                category_id=category_id,
                session=session,
            )

            session.add(
                Match(
                    tournament_id=tournament_id,
                    category_id=category_id,
                    round=1,
                    position=1,
                    match_type="ELIMINATION",
                )
            )
            session.commit()

            with pytest.raises(ValidationError) as exc_info:
                generate_bracket(
                    tournament_id=tournament_id,
                    category_id=category_id,
                    session=session,
                )

        assert exc_info.value.code == "BRACKET_ALREADY_EXISTS"

    @staticmethod
    def test_legacy_standalone_model_files_removed() -> None:
        """Dead standalone model files should be deleted after consolidation."""
        assert not (REPO_ROOT / "kakumi_app/models/penalty_model.py").exists()
        assert not (REPO_ROOT / "kakumi_app/models/tournament_area_model.py").exists()

    @staticmethod
    def test_alembic_bracket_side_migration(
        tmp_path: Path,
        alembic_config_for_db,
    ) -> None:
        """Upgrade adds bracket_side and downgrade removes it."""
        db_url = f"sqlite:///{tmp_path / 'bracket_side.sqlite'}"
        config = alembic_config_for_db(db_url)

        command.upgrade(config, "head")

        upgraded_columns = {
            column["name"]
            for column in sa.inspect(create_engine(db_url)).get_columns("matches")
        }
        assert "bracket_side" in upgraded_columns

        # Downgrade to the revision before bracket_side was introduced.
        command.downgrade(config, "1a9f9cf5faa1")

        downgraded_columns = {
            column["name"]
            for column in sa.inspect(create_engine(db_url)).get_columns("matches")
        }
        assert "bracket_side" not in downgraded_columns

    @staticmethod
    def test_match_bracket_side_persistence() -> None:
        """Match.bracket_side should round-trip through the ORM."""
        from kakumi_app.models.tournament_model import BracketSide, Match

        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            tournament = _make_tournament()
            session.add(tournament)
            session.flush()

            category = _make_category(tournament.id)
            session.add(category)
            session.flush()

            match = Match(
                tournament_id=tournament.id,
                category_id=category.id,
                round=1,
                position=1,
                match_type="ELIMINATION",
                bracket_side=BracketSide.WINNERS.value,
            )
            session.add(match)
            session.commit()
            session.refresh(match)

            reloaded = session.query(Match).filter(Match.id == match.id).first()

        assert match.bracket_side == BracketSide.WINNERS.value
        assert reloaded is not None
        assert reloaded.bracket_side == BracketSide.WINNERS.value
