"""
KAKUMI Test Configuration
=========================
Fixtures y configuración compartida para todos los tests.
Usa DB SQLite aislada por test para evitar contaminación entre tests.
"""

import datetime
import os
from collections.abc import Callable
from pathlib import Path
from typing import Generator

import pytest
import reflex as rx
import sqlmodel
import sqlalchemy as sa
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.kata_model import (  # noqa: F401
    KataJudgeScore,
    KataRoundStanding,
)
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
    Tatami,
    Tournament,
    TournamentCategory,
    TournamentStatus,
)
from kakumi_app.models.user_model import User, UserRole


FK_TARGET_INDEXES: dict[str, set[str]] = {
    "athletes": {
        "ix_athletes_kata_category_id",
        "ix_athletes_kumite_category_id",
    },
    "matches": {
        "ix_matches_aka_id",
        "ix_matches_ao_id",
        "ix_matches_winner_id",
        "ix_matches_aka_team_id",
        "ix_matches_ao_team_id",
        "ix_matches_referee_id",
        "ix_matches_tatami_id",
    },
    "match_scores": {
        "ix_match_scores_judge_id",
        "ix_match_scores_applied_by_id",
    },
    "penalties": {
        "ix_penalties_given_by_id",
    },
    "tournament_categories": {
        "ix_tournament_categories_first_place_id",
        "ix_tournament_categories_second_place_id",
    },
    "token_blacklist": {
        "ix_token_blacklist_user_id",
    },
    "tournament_event_logs": {
        "ix_tournament_event_logs_user_id",
    },
    "kata_judge_scores": {
        "ix_kata_judge_scores_performer_id",
        "ix_kata_judge_scores_team_id",
    },
    "kata_round_standings": {
        "ix_kata_round_standings_athlete_id",
        "ix_kata_round_standings_team_id",
    },
}


@pytest.fixture
def fk_target_indexes() -> dict[str, set[str]]:
    """Return canonical FK index targets for db-schema-indexes."""
    return FK_TARGET_INDEXES


@pytest.fixture
def fk_index_migration_path() -> Path:
    """Return path to FK index migration revision file."""
    return (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "c078f55c0552_add_fk_indexes.py"
    )


@pytest.fixture
def alembic_config_for_db() -> Callable[[str], Config]:
    """Factory fixture returning alembic config for a DB URL."""

    def _factory(db_url: str) -> Config:
        project_root = Path(__file__).resolve().parents[1]
        config = Config(str(project_root / "alembic.ini"))
        config.set_main_option("script_location", str(project_root / "alembic"))
        config.set_main_option("sqlalchemy.url", db_url)
        return config

    return _factory


@pytest.fixture
def index_names_for_tables() -> Callable[
    [str, dict[str, set[str]]], tuple[set[str], dict[str, set[str]]]
]:
    """Factory fixture for index inspection by explicit table set."""

    def _factory(
        db_url: str,
        target_indexes: dict[str, set[str]],
    ) -> tuple[set[str], dict[str, set[str]]]:
        engine = sa.create_engine(db_url)
        inspector = sa.inspect(engine)
        existing_tables = set(inspector.get_table_names())

        indexes_by_table: dict[str, set[str]] = {}
        for table_name in target_indexes:
            if table_name not in existing_tables:
                indexes_by_table[table_name] = set()
                continue

            indexes = inspector.get_indexes(table_name)
            indexes_by_table[table_name] = {index["name"] for index in indexes}

        engine.dispose()
        return existing_tables, indexes_by_table

    return _factory


# DB de test separada de la producción
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_kakumi.db")
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"


@pytest.fixture(scope="function", autouse=True)
def db_session(monkeypatch: pytest.MonkeyPatch) -> Generator[Session, None, None]:
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


@pytest.fixture(scope="function")
def in_memory_session(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[Session, None, None]:
    """Provide an isolated in-memory SQLite session for focused tests."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def _test_session(url: str | None = None) -> Session:
        """Return sessions bound to the in-memory engine."""
        del url
        return Session(engine)

    monkeypatch.setattr(rx.model, "session", _test_session)

    with Session(engine) as session:
        yield session

    engine.dispose()


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


@pytest.fixture(scope="function")
def sample_team_2(sample_category: TournamentCategory) -> Team:
    """Crea segundo equipo de prueba para escenarios Team Kata."""
    with rx.session() as session:
        team = Team(
            name="Equipo Dojo Norte",
            category_id=sample_category.id,
            member_count=0,
            is_active=True,
            dojo="Dojo Norte",
        )
        session.add(team)
        session.commit()
        session.refresh(team)
        return team


@pytest.fixture(scope="function")
def sample_judges() -> Callable[[int], list[Referee]]:
    """Factory de jueces disponibles para panel de Kata."""

    def _factory(n: int = 5) -> list[Referee]:
        judges: list[Referee] = []
        with rx.session() as session:
            for index in range(n):
                judge = Referee(
                    name=f"Juez Kata {index + 1}",
                    license_number=f"JUDGE-KATA-{index + 1:03d}",
                    license_level="INTERNATIONAL",
                    role="JUDGE",
                    is_available=True,
                    dojo="Panel Kata",
                    email=f"judge{index + 1}@kata.test",
                )
                session.add(judge)
                judges.append(judge)
            session.commit()
            for judge in judges:
                session.refresh(judge)
        return judges

    return _factory


@pytest.fixture(scope="function")
def kata_category(sample_tournament: Tournament) -> TournamentCategory:
    """Categoría base de Kata individual para tests de scoring."""
    with rx.session() as session:
        category = TournamentCategory(
            name="Kata Individual Senior",
            modality=Modality.KATA_INDIVIDUAL.value,
            gender=CategoryGender.MIXED.value,
            min_age=16,
            max_age=40,
            competition_system=CompetitionSystem.ROUND_ROBIN.value,
            bracket_size=8,
            status=CategoryStatus.PENDING.value,
            tournament_id=sample_tournament.id,
            judge_panel_size=5,
            bunkai_mode="NONE",
        )
        session.add(category)
        session.commit()
        session.refresh(category)
        return category


@pytest.fixture(scope="function")
def kata_team_category(
    sample_tournament: Tournament,
) -> Callable[[str], TournamentCategory]:
    """Factory de categoría Team Kata con bunkai_mode configurable."""

    def _factory(bunkai_mode: str = "NONE") -> TournamentCategory:
        with rx.session() as session:
            category = TournamentCategory(
                name=f"Kata Team {bunkai_mode}",
                modality=Modality.KATA_TEAM.value,
                gender=CategoryGender.MIXED.value,
                min_age=16,
                max_age=40,
                competition_system=CompetitionSystem.ROUND_ROBIN.value,
                bracket_size=8,
                status=CategoryStatus.PENDING.value,
                tournament_id=sample_tournament.id,
                judge_panel_size=5,
                bunkai_mode=bunkai_mode,
            )
            session.add(category)
            session.commit()
            session.refresh(category)
            return category

    return _factory


@pytest.fixture(scope="function")
def kata_match(
    kata_category: TournamentCategory,
    sample_athlete: Athlete,
    sample_athlete_2: Athlete,
    sample_referee: Referee,
    sample_tatami: Tatami,
) -> Match:
    """Match Kata individual vinculado a kata_category."""
    with rx.session() as session:
        match = Match(
            round=1,
            match_number=1,
            position=0,
            match_type=MatchType.ROUND_ROBIN.value,
            category_id=kata_category.id,
            aka_id=sample_athlete.id,
            ao_id=sample_athlete_2.id,
            status=MatchStatus.PENDING.value,
            tatami_id=sample_tatami.id,
            referee_id=sample_referee.id,
        )
        session.add(match)
        session.commit()
        session.refresh(match)
        return match


@pytest.fixture(scope="function")
def rr_pool_fixture(
    in_memory_session: Session,
) -> Generator[dict[str, int], None, None]:
    """Create a 3-athlete round-robin pool with 3 matches.

    Yields:
        Dict with ids for tournament/category/referee/athletes/matches.
    """
    tournament = Tournament(
        name="Penalty RR Pool",
        venue="Dojo RR",
        start_date=datetime.date(2026, 9, 1),
        end_date=datetime.date(2026, 9, 1),
        status=TournamentStatus.PLANIFICADO.value,
        tatami_count=2,
        is_public=True,
    )
    in_memory_session.add(tournament)
    in_memory_session.commit()
    in_memory_session.refresh(tournament)

    category = TournamentCategory(
        name="Kumite RR Integration",
        modality=Modality.KUMITE_INDIVIDUAL.value,
        competition_system=CompetitionSystem.ROUND_ROBIN.value,
        tournament_id=tournament.id,
        match_duration_seconds=180,
    )
    in_memory_session.add(category)
    in_memory_session.commit()
    in_memory_session.refresh(category)

    referee = Referee(
        name="RR Referee",
        license_number="RR-REF-001",
        license_level="INTERNATIONAL",
        role="REFEREE",
        is_available=True,
        dojo="Dojo RR",
        email="rr-ref@test.dev",
    )
    in_memory_session.add(referee)
    in_memory_session.commit()
    in_memory_session.refresh(referee)

    athlete_a = Athlete(
        name="RR Athlete A",
        date_of_birth=datetime.date(2000, 1, 1),
        gender="MALE",
        email="rr-athlete-a@test.dev",
        belt_rank="Dan 1",
        is_active=True,
    )
    athlete_b = Athlete(
        name="RR Athlete B",
        date_of_birth=datetime.date(2000, 1, 1),
        gender="MALE",
        email="rr-athlete-b@test.dev",
        belt_rank="Dan 1",
        is_active=True,
    )
    athlete_c = Athlete(
        name="RR Athlete C",
        date_of_birth=datetime.date(2000, 1, 1),
        gender="MALE",
        email="rr-athlete-c@test.dev",
        belt_rank="Dan 1",
        is_active=True,
    )
    in_memory_session.add(athlete_a)
    in_memory_session.add(athlete_b)
    in_memory_session.add(athlete_c)
    in_memory_session.commit()
    in_memory_session.refresh(athlete_a)
    in_memory_session.refresh(athlete_b)
    in_memory_session.refresh(athlete_c)

    tatami_1 = Tatami(
        name="RR Tatami 1",
        location="Zone 1",
        is_active=True,
        tournament_id=tournament.id,
    )
    tatami_2 = Tatami(
        name="RR Tatami 2",
        location="Zone 2",
        is_active=True,
        tournament_id=tournament.id,
    )
    in_memory_session.add(tatami_1)
    in_memory_session.add(tatami_2)
    in_memory_session.commit()
    in_memory_session.refresh(tatami_1)
    in_memory_session.refresh(tatami_2)

    match_1 = Match(
        round=1,
        match_number=1,
        position=1,
        match_type=MatchType.ROUND_ROBIN.value,
        category_id=category.id,
        aka_id=athlete_a.id,
        ao_id=athlete_b.id,
        aka_score=4,
        ao_score=1,
        winner_id=athlete_a.id,
        status=MatchStatus.COMPLETED.value,
        tatami_id=tatami_1.id,
        referee_id=referee.id,
        start_time=datetime.datetime(2026, 9, 1, 10, 0, 0),
    )
    match_2 = Match(
        round=1,
        match_number=2,
        position=2,
        match_type=MatchType.ROUND_ROBIN.value,
        category_id=category.id,
        aka_id=athlete_a.id,
        ao_id=athlete_c.id,
        aka_score=0,
        ao_score=0,
        status=MatchStatus.IN_PROGRESS.value,
        tatami_id=tatami_1.id,
        referee_id=referee.id,
        start_time=datetime.datetime(2026, 9, 1, 10, 5, 0),
    )
    match_3 = Match(
        round=1,
        match_number=3,
        position=3,
        match_type=MatchType.ROUND_ROBIN.value,
        category_id=category.id,
        aka_id=athlete_b.id,
        ao_id=athlete_c.id,
        aka_score=2,
        ao_score=0,
        winner_id=athlete_b.id,
        status=MatchStatus.COMPLETED.value,
        tatami_id=tatami_2.id,
        referee_id=referee.id,
        start_time=datetime.datetime(2026, 9, 1, 10, 10, 0),
    )
    in_memory_session.add(match_1)
    in_memory_session.add(match_2)
    in_memory_session.add(match_3)
    in_memory_session.commit()
    in_memory_session.refresh(match_1)
    in_memory_session.refresh(match_2)
    in_memory_session.refresh(match_3)

    yield {
        "tournament_id": tournament.id,
        "category_id": category.id,
        "referee_id": referee.id,
        "dq_athlete_id": athlete_a.id,
        "opponent_1_id": athlete_b.id,
        "opponent_2_id": athlete_c.id,
        "previous_match_id": match_1.id,
        "current_match_id": match_2.id,
        "pool_match_id": match_3.id,
        "tatami_1_id": tatami_1.id,
        "tatami_2_id": tatami_2.id,
    }


@pytest.fixture(scope="function")
def team_match_fixture(
    in_memory_session: Session,
) -> Generator[dict[str, object], None, None]:
    """Create one in-progress team match with two 3-athlete teams.

    Yields:
        Dict with match id and both team athlete ids.
    """
    tournament = Tournament(
        name="Penalty Team Tournament",
        venue="Dojo Team",
        start_date=datetime.date(2026, 9, 2),
        end_date=datetime.date(2026, 9, 2),
        status=TournamentStatus.PLANIFICADO.value,
        tatami_count=1,
        is_public=True,
    )
    in_memory_session.add(tournament)
    in_memory_session.commit()
    in_memory_session.refresh(tournament)

    category = TournamentCategory(
        name="Kumite Team Integration",
        modality=Modality.KUMITE_TEAM.value,
        competition_system=CompetitionSystem.ELIMINATION.value,
        tournament_id=tournament.id,
    )
    in_memory_session.add(category)
    in_memory_session.commit()
    in_memory_session.refresh(category)

    referee = Referee(
        name="Team Referee",
        license_number="TEAM-REF-001",
        license_level="INTERNATIONAL",
        role="REFEREE",
        is_available=True,
        dojo="Dojo Team",
        email="team-ref@test.dev",
    )
    in_memory_session.add(referee)
    in_memory_session.commit()
    in_memory_session.refresh(referee)

    aka_team = Team(
        name="AKA Team Integration",
        category_id=category.id,
        member_count=3,
        is_active=True,
    )
    ao_team = Team(
        name="AO Team Integration",
        category_id=category.id,
        member_count=3,
        is_active=True,
    )
    in_memory_session.add(aka_team)
    in_memory_session.add(ao_team)
    in_memory_session.commit()
    in_memory_session.refresh(aka_team)
    in_memory_session.refresh(ao_team)

    aka_ids: list[int] = []
    ao_ids: list[int] = []
    for index in range(3):
        aka_athlete = Athlete(
            name=f"Team AKA Athlete {index + 1}",
            date_of_birth=datetime.date(2000, 1, 1),
            gender="MALE",
            email=f"team-aka-{index + 1}@test.dev",
            belt_rank="Dan 1",
            is_active=True,
        )
        ao_athlete = Athlete(
            name=f"Team AO Athlete {index + 1}",
            date_of_birth=datetime.date(2000, 1, 1),
            gender="MALE",
            email=f"team-ao-{index + 1}@test.dev",
            belt_rank="Dan 1",
            is_active=True,
        )
        in_memory_session.add(aka_athlete)
        in_memory_session.add(ao_athlete)
        in_memory_session.commit()
        in_memory_session.refresh(aka_athlete)
        in_memory_session.refresh(ao_athlete)
        aka_ids.append(aka_athlete.id)
        ao_ids.append(ao_athlete.id)

        in_memory_session.add(
            TeamMember(
                team_id=aka_team.id,
                athlete_id=aka_athlete.id,
                position=index + 1,
                is_reserve=False,
            )
        )
        in_memory_session.add(
            TeamMember(
                team_id=ao_team.id,
                athlete_id=ao_athlete.id,
                position=index + 1,
                is_reserve=False,
            )
        )

    in_memory_session.commit()

    match = Match(
        round=1,
        match_number=1,
        position=1,
        match_type=MatchType.ELIMINATION.value,
        category_id=category.id,
        aka_team_id=aka_team.id,
        ao_team_id=ao_team.id,
        status=MatchStatus.IN_PROGRESS.value,
        referee_id=referee.id,
        aka_score=0,
        ao_score=0,
    )
    in_memory_session.add(match)
    in_memory_session.commit()
    in_memory_session.refresh(match)

    yield {
        "match_id": match.id,
        "aka_team_id": aka_team.id,
        "ao_team_id": ao_team.id,
        "aka_athlete_ids": aka_ids,
        "ao_athlete_ids": ao_ids,
    }


@pytest.fixture(scope="function")
def tatami_fixture(
    in_memory_session: Session,
) -> Generator[dict[str, int], None, None]:
    """Create overlapping same-athlete matches on different tatamis.

    Yields:
        Dict with target match, athlete and conflict match identifiers.
    """
    tournament = Tournament(
        name="Tatami Overlap Tournament",
        venue="Dojo Tatami",
        start_date=datetime.date(2026, 9, 3),
        end_date=datetime.date(2026, 9, 3),
        status=TournamentStatus.PLANIFICADO.value,
        tatami_count=2,
        is_public=True,
    )
    in_memory_session.add(tournament)
    in_memory_session.commit()
    in_memory_session.refresh(tournament)

    category = TournamentCategory(
        name="Kumite Tatami Integration",
        modality=Modality.KUMITE_INDIVIDUAL.value,
        competition_system=CompetitionSystem.ELIMINATION.value,
        tournament_id=tournament.id,
        match_duration_seconds=180,
    )
    in_memory_session.add(category)
    in_memory_session.commit()
    in_memory_session.refresh(category)

    referee = Referee(
        name="Tatami Referee",
        license_number="TATAMI-REF-001",
        license_level="INTERNATIONAL",
        role="REFEREE",
        is_available=True,
        dojo="Dojo Tatami",
        email="tatami-ref@test.dev",
    )
    in_memory_session.add(referee)
    in_memory_session.commit()
    in_memory_session.refresh(referee)

    shared_athlete = Athlete(
        name="Tatami Shared Athlete",
        date_of_birth=datetime.date(2000, 1, 1),
        gender="MALE",
        email="tatami-shared@test.dev",
        belt_rank="Dan 1",
        is_active=True,
    )
    opponent_a = Athlete(
        name="Tatami Opponent A",
        date_of_birth=datetime.date(2000, 1, 1),
        gender="MALE",
        email="tatami-opponent-a@test.dev",
        belt_rank="Dan 1",
        is_active=True,
    )
    opponent_b = Athlete(
        name="Tatami Opponent B",
        date_of_birth=datetime.date(2000, 1, 1),
        gender="MALE",
        email="tatami-opponent-b@test.dev",
        belt_rank="Dan 1",
        is_active=True,
    )
    in_memory_session.add(shared_athlete)
    in_memory_session.add(opponent_a)
    in_memory_session.add(opponent_b)
    in_memory_session.commit()
    in_memory_session.refresh(shared_athlete)
    in_memory_session.refresh(opponent_a)
    in_memory_session.refresh(opponent_b)

    tatami_a = Tatami(
        name="Tatami Overlap A",
        location="Zone A",
        is_active=True,
        tournament_id=tournament.id,
    )
    tatami_b = Tatami(
        name="Tatami Overlap B",
        location="Zone B",
        is_active=True,
        tournament_id=tournament.id,
    )
    in_memory_session.add(tatami_a)
    in_memory_session.add(tatami_b)
    in_memory_session.commit()
    in_memory_session.refresh(tatami_a)
    in_memory_session.refresh(tatami_b)

    conflict_match = Match(
        round=1,
        match_number=1,
        position=1,
        match_type=MatchType.ELIMINATION.value,
        category_id=category.id,
        aka_id=shared_athlete.id,
        ao_id=opponent_a.id,
        status=MatchStatus.IN_PROGRESS.value,
        tatami_id=tatami_a.id,
        referee_id=referee.id,
        start_time=datetime.datetime(2026, 9, 3, 10, 0, 0),
    )
    target_match = Match(
        round=1,
        match_number=2,
        position=2,
        match_type=MatchType.ELIMINATION.value,
        category_id=category.id,
        aka_id=shared_athlete.id,
        ao_id=opponent_b.id,
        status=MatchStatus.READY.value,
        tatami_id=tatami_b.id,
        referee_id=referee.id,
        start_time=datetime.datetime(2026, 9, 3, 10, 2, 0),
    )
    in_memory_session.add(conflict_match)
    in_memory_session.add(target_match)
    in_memory_session.commit()
    in_memory_session.refresh(conflict_match)
    in_memory_session.refresh(target_match)

    yield {
        "athlete_id": shared_athlete.id,
        "target_match_id": target_match.id,
        "conflict_match_id": conflict_match.id,
        "category_id": category.id,
    }
