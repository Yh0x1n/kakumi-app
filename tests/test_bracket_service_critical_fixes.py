"""Critical regression coverage for bracket service foundations."""

import datetime
import importlib
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from sqlmodel import SQLModel, Session, create_engine

from kakumi_app.services.tournament_service import ValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]


def _make_tournament():
    from kakumi_app.models.tournament_model import Tournament, TournamentStatus

    return Tournament(
        name="Critical Fix Tournament",
        venue="Dojo Central",
        start_date=datetime.date(2026, 4, 27),
        end_date=datetime.date(2026, 4, 28),
        status=TournamentStatus.VERIFICACION.value,
    )


def _make_category(tournament_id: int):
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


def test_no_sqlalchemy_mapper_conflict() -> None:
    """Importing models should register one usable Match mapper."""
    models = importlib.import_module("kakumi_app.models")
    tournament_models = importlib.import_module("kakumi_app.models.tournament_model")

    assert models.Match is tournament_models.Match
    assert models.Match.__tablename__ == "matches"


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


def test_bracket_service_guard_existing_matches() -> None:
    """generate_bracket() must re-check and block regeneration."""
    from kakumi_app.models.tournament_model import Match

    bracket_module = importlib.import_module(
        "kakumi_app.services" + ".bracket_service"
    )
    BracketService = bracket_module.BracketService

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

        service = BracketService(
            tournament_id=tournament_id,
            category_id=category_id,
            session=session,
        )

        first_result = service.generate_bracket()

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
            service.generate_bracket()

    assert first_result == {
        "tournament_id": tournament_id,
        "category_id": category_id,
        "status": "ready",
    }

    assert exc_info.value.code == "BRACKET_ALREADY_EXISTS"
    assert (
        exc_info.value.message
        == "Bracket already generated for this category. Cannot regenerate."
    )


def test_legacy_standalone_model_files_removed() -> None:
    """Dead standalone model files should be deleted after consolidation."""

    assert not (REPO_ROOT / "kakumi_app/models/penalty_model.py").exists()
    assert not (REPO_ROOT / "kakumi_app/models/tournament_area_model.py").exists()


def test_bracket_service_generate_no_existing_matches() -> None:
    """Bracket generation placeholder should succeed for an empty category."""
    bracket_module = importlib.import_module(
        "kakumi_app.services" + ".bracket_service"
    )
    BracketService = bracket_module.BracketService

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        tournament = _make_tournament()
        session.add(tournament)
        session.flush()

        category = _make_category(tournament.id)
        session.add(category)
        session.commit()

        service = BracketService(
            tournament_id=tournament.id,
            category_id=category.id,
            session=session,
        )

        result = service.generate_bracket()

    assert result == {
        "tournament_id": tournament.id,
        "category_id": category.id,
        "status": "ready",
    }


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

    command.downgrade(config, "-1")

    downgraded_columns = {
        column["name"]
        for column in sa.inspect(create_engine(db_url)).get_columns("matches")
    }
    assert "bracket_side" not in downgraded_columns


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
