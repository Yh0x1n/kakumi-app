"""Tests for winner propagation in elimination brackets."""

import datetime

import pytest
import reflex as rx
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.tournament_model import (
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
    propagate_winner,
)


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


def test_propagate_odd_position_winner_to_next_aka() -> None:
    """Winner from odd-position match (pos=1) fills aka_id in next round."""
    tournament = _create_tournament()
    category = _create_category(tournament.id)
    athletes = _create_athletes(4)

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


def test_propagate_even_position_winner_to_next_ao() -> None:
    """Winner from even-position match (pos=2) fills ao_id in next round."""
    tournament = _create_tournament()
    category = _create_category(tournament.id)
    athletes = _create_athletes(4)

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


def test_propagate_both_sides_fill_final_correctly() -> None:
    """Both semis propagate — both aka_id and ao_id set in final."""
    tournament = _create_tournament()
    category = _create_category(tournament.id)
    athletes = _create_athletes(4)

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


def test_propagate_idempotent_when_slot_already_filled() -> None:
    """Second call does not overwrite a slot that is already filled."""
    tournament = _create_tournament()
    category = _create_category(tournament.id)
    athletes = _create_athletes(4)

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


def test_propagate_no_winner_id_does_nothing() -> None:
    """Match with winner_id=None does not propagate."""
    tournament = _create_tournament()
    category = _create_category(tournament.id)
    athletes = _create_athletes(4)

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


def test_propagate_on_8_participant_bracket() -> None:
    """Verify positional math on a deeper bracket (3 rounds)."""
    tournament = _create_tournament("8 Participant Bracket")
    category = _create_category(tournament.id)
    athletes = _create_athletes(8)

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
