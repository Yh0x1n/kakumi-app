"""
KAKUMI Test Configuration
=========================
Fixtures y configuración compartida para todos los tests.
Usa DB SQLite aislada por test para evitar contaminación entre tests.
"""

import datetime
import os
from typing import Generator

import pytest
import reflex as rx
import sqlmodel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.referee_model import Referee
from kakumi_app.models.team_model import Team, TeamMember
from kakumi_app.models.tournament_model import (
    CategoryGender,
    CategoryStatus,
    CompetitionSystem,
    Match,
    MatchStatus,
    MatchType,
    Modality,
    Penalty,
    PenaltyType,
    ScoreType,
    Tatami,
    Tournament,
    TournamentCategory,
    TournamentStatus,
)
from kakumi_app.models.user_model import User, UserRole

# DB de test separada de la producción
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_kakumi.db")
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"


@pytest.fixture(scope="function", autouse=True)
def db_session(monkeypatch) -> Generator[Session, None, None]:
    """
    Crea una DB de test aislada por cada test function.

    - Usa una DB SQLite de test separada de la producción
    - Crea todas las tablas antes del test
    - Parchea rx.session() para que use la DB de test
    - Elimina la DB después de cada test
    """
    # Eliminar DB de test previa si existe
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    # Crear engine de test
    test_engine = create_engine(TEST_DB_URL, echo=False)

    # Crear todas las tablas en la DB de test
    # rx.Model hereda de SQLModel, así que SQLModel.metadata tiene todos los modelos
    SQLModel.metadata.create_all(test_engine)

    # Parchear rx.model.session para que use la DB de test
    def _test_session(url: str | None = None) -> sqlmodel.Session:
        """Session que usa la DB de test en lugar de la de producción."""
        return sqlmodel.Session(test_engine)

    monkeypatch.setattr(rx.model, "session", _test_session)

    # Yield session para tests que la necesiten directamente
    with sqlmodel.Session(test_engine) as session:
        yield session

    # Cleanup: destruir engine y eliminar DB de test
    test_engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


# =============================================================================
# FIXTURES DE DATOS
# =============================================================================


@pytest.fixture(scope="function")
def sample_user() -> User:
    """Crea un usuario de prueba y lo retorna."""
    with rx.session() as session:
        user = User(
            username="test_admin",
            email="admin@kakumi.test",
            password_hash="hashed_password_123",
            full_name="Test Admin User",
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@pytest.fixture(scope="function")
def sample_tournament(sample_user: User) -> Tournament:
    """Crea un torneo de prueba vinculado al usuario."""
    with rx.session() as session:
        tournament = Tournament(
            name="Torneo de Prueba Kakumi",
            venue="Dojo Central",
            start_date=datetime.date(2026, 6, 1),
            end_date=datetime.date(2026, 6, 3),
            tatami_count=2,
            status=TournamentStatus.PLANIFICADO.value,
            is_public=True,
            description="Torneo de prueba para tests unitarios",
            created_by_id=sample_user.id,
        )
        session.add(tournament)
        session.commit()
        session.refresh(tournament)
        return tournament


@pytest.fixture(scope="function")
def sample_category(sample_tournament: Tournament) -> TournamentCategory:
    """Crea una categoría de prueba Kata Individual Masculina."""
    with rx.session() as session:
        category = TournamentCategory(
            name="Kata Individual Masculino Senior",
            modality=Modality.KATA_INDIVIDUAL.value,
            gender=CategoryGender.MALE.value,
            min_age=18,
            max_age=35,
            competition_system=CompetitionSystem.ELIMINATION.value,
            bracket_size=8,
            status=CategoryStatus.PENDING.value,
            tournament_id=sample_tournament.id,
            judge_panel_size=5,
        )
        session.add(category)
        session.commit()
        session.refresh(category)
        return category


@pytest.fixture(scope="function")
def sample_athlete() -> Athlete:
    """Crea un atleta de prueba."""
    with rx.session() as session:
        athlete = Athlete(
            name="Carlos Martinez",
            date_of_birth=datetime.date(1998, 5, 15),
            gender="MALE",
            email="carlos@dojo.test",
            weight_kg=72.5,
            belt_rank="Dan 2",
            dojo="Dojo Shoto",
            nationality="ARG",
            license_number="LIC-001",
            is_active=True,
        )
        session.add(athlete)
        session.commit()
        session.refresh(athlete)
        return athlete


@pytest.fixture(scope="function")
def sample_athlete_2() -> Athlete:
    """Crea un segundo atleta de prueba."""
    with rx.session() as session:
        athlete = Athlete(
            name="Ana Rodriguez",
            date_of_birth=datetime.date(2000, 8, 22),
            gender="FEMALE",
            email="ana@dojo.test",
            weight_kg=58.0,
            belt_rank="Dan 1",
            dojo="Dojo Shoto",
            nationality="ARG",
            license_number="LIC-002",
            is_active=True,
        )
        session.add(athlete)
        session.commit()
        session.refresh(athlete)
        return athlete


@pytest.fixture(scope="function")
def sample_referee() -> Referee:
    """Crea un árbitro de prueba."""
    with rx.session() as session:
        referee = Referee(
            name="Juez Principal",
            license_number="REF-001",
            license_level="INTERNATIONAL",
            role="REFEREE",
            is_available=True,
            dojo="Federacion Central",
            email="juez@fed.test",
        )
        session.add(referee)
        session.commit()
        session.refresh(referee)
        return referee


@pytest.fixture(scope="function")
def sample_tatami(sample_tournament: Tournament) -> Tatami:
    """Crea un tatami de prueba."""
    with rx.session() as session:
        tatami = Tatami(
            name="Tatami 1",
            location="Sector A",
            is_active=True,
            tournament_id=sample_tournament.id,
        )
        session.add(tatami)
        session.commit()
        session.refresh(tatami)
        return tatami


@pytest.fixture(scope="function")
def sample_match(
    sample_category: TournamentCategory,
    sample_athlete: Athlete,
    sample_athlete_2: Athlete,
    sample_referee: Referee,
    sample_tatami: Tatami,
) -> Match:
    """Crea un encuentro de prueba completo."""
    with rx.session() as session:
        match = Match(
            round=1,
            match_number=1,
            position=0,
            match_type=MatchType.ELIMINATION.value,
            category_id=sample_category.id,
            aka_id=sample_athlete.id,
            ao_id=sample_athlete_2.id,
            aka_score=0,
            ao_score=0,
            status=MatchStatus.PENDING.value,
            tatami_id=sample_tatami.id,
            referee_id=sample_referee.id,
        )
        session.add(match)
        session.commit()
        session.refresh(match)
        return match


@pytest.fixture(scope="function")
def sample_team(sample_category: TournamentCategory) -> Team:
    """Crea un equipo de prueba."""
    with rx.session() as session:
        team = Team(
            name="Equipo Dojo Shoto",
            category_id=sample_category.id,
            member_count=0,
            is_active=True,
            dojo="Dojo Shoto",
        )
        session.add(team)
        session.commit()
        session.refresh(team)
        return team
