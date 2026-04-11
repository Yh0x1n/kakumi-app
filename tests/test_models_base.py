"""
KAKUMI Tests - Modelos Base
============================
Tests para: Athlete, Tournament, TournamentCategory
Cubre: CRUD, relaciones, enums, validaciones de campos.
"""

import datetime

import pytest
import reflex as rx
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete, AthleteGender
from kakumi_app.models.tournament_model import (
    CategoryGender,
    CategoryStatus,
    CompetitionSystem,
    Modality,
    Tournament,
    TournamentCategory,
    TournamentStatus,
)


# =============================================================================
# ATHLETE TESTS
# =============================================================================


class TestAthleteCRUD:
    """Tests de crear, leer, actualizar y eliminar Athlete."""

    def test_create_athlete(self, sample_athlete):
        """Un atleta creado tiene los campos correctos y un ID asignado."""
        assert sample_athlete.id is not None
        assert sample_athlete.name == "Carlos Martinez"
        assert sample_athlete.date_of_birth == datetime.date(1998, 5, 15)
        assert sample_athlete.gender == "MALE"
        assert sample_athlete.email == "carlos@dojo.test"
        assert sample_athlete.weight_kg == 72.5
        assert sample_athlete.belt_rank == "Dan 2"
        assert sample_athlete.dojo == "Dojo Shoto"
        assert sample_athlete.nationality == "ARG"
        assert sample_athlete.license_number == "LIC-001"
        assert sample_athlete.is_active is True

    def test_create_athlete_minimal(self):
        """Un atleta se puede crear solo con campos obligatorios."""
        with rx.session() as session:
            athlete = Athlete(
                name="Atleta Minimo",
                date_of_birth=datetime.date(2005, 1, 1),
                gender="MALE",
            )
            session.add(athlete)
            session.commit()
            session.refresh(athlete)

            assert athlete.id is not None
            assert athlete.name == "Atleta Minimo"
            assert athlete.email is None
            assert athlete.weight_kg is None
            assert athlete.belt_rank is None
            assert athlete.is_active is True  # default

    def test_read_athlete_by_id(self, sample_athlete):
        """Se puede recuperar un atleta por su ID."""
        with rx.session() as session:
            result = session.get(Athlete, sample_athlete.id)
            assert result is not None
            assert result.name == "Carlos Martinez"

    def test_read_athlete_by_name(self, sample_athlete):
        """Se puede buscar un atleta por nombre usando select."""
        with rx.session() as session:
            query = select(Athlete).where(Athlete.name == "Carlos Martinez")
            result = session.exec(query).first()
            assert result is not None
            assert result.id == sample_athlete.id

    def test_update_athlete(self, sample_athlete):
        """Se puede actualizar un campo del atleta."""
        with rx.session() as session:
            athlete = session.get(Athlete, sample_athlete.id)
            athlete.weight_kg = 75.0
            athlete.belt_rank = "Dan 3"
            session.add(athlete)
            session.commit()
            session.refresh(athlete)

            assert athlete.weight_kg == 75.0
            assert athlete.belt_rank == "Dan 3"

    def test_delete_athlete(self):
        """Se puede eliminar un atleta de la base de datos."""
        with rx.session() as session:
            athlete = Athlete(
                name="Atleta Eliminable",
                date_of_birth=datetime.date(2000, 1, 1),
                gender="FEMALE",
            )
            session.add(athlete)
            session.commit()
            athlete_id = athlete.id

            session.delete(athlete)
            session.commit()

            result = session.get(Athlete, athlete_id)
            assert result is None

    def test_athlete_unique_name(self, sample_athlete):
        """No se puede crear un segundo atleta con el mismo nombre (unique)."""
        with rx.session() as session:
            duplicate = Athlete(
                name="Carlos Martinez",
                date_of_birth=datetime.date(2000, 1, 1),
                gender="MALE",
            )
            session.add(duplicate)
            with pytest.raises(Exception):
                session.commit()
            session.rollback()

    def test_athlete_unique_email(self, sample_athlete):
        """No se puede crear un segundo atleta con el mismo email (unique)."""
        with rx.session() as session:
            duplicate = Athlete(
                name="Otro Atleta",
                date_of_birth=datetime.date(2000, 1, 1),
                gender="MALE",
                email="carlos@dojo.test",
            )
            session.add(duplicate)
            with pytest.raises(Exception):
                session.commit()
            session.rollback()


class TestAthleteFields:
    """Tests de validación de campos y defaults del modelo Athlete."""

    def test_athlete_is_active_default_true(self):
        """is_active defaultea a True."""
        with rx.session() as session:
            athlete = Athlete(
                name="Activo Default",
                date_of_birth=datetime.date(2000, 1, 1),
                gender="MALE",
            )
            session.add(athlete)
            session.commit()
            session.refresh(athlete)
            assert athlete.is_active is True

    def test_athlete_created_at_auto(self):
        """created_at se asigna automáticamente al crear."""
        with rx.session() as session:
            athlete = Athlete(
                name="Timestamp Test",
                date_of_birth=datetime.date(2000, 1, 1),
                gender="MALE",
            )
            session.add(athlete)
            session.commit()
            session.refresh(athlete)
            assert athlete.created_at is not None

    def test_athlete_gender_enum_values(self):
        """AthleteGender enum tiene los valores correctos."""
        assert AthleteGender.MALE.value == "MALE"
        assert AthleteGender.FEMALE.value == "FEMALE"

    def test_athlete_gender_stored_as_string(self, sample_athlete):
        """El género se almacena como string, no como enum."""
        assert isinstance(sample_athlete.gender, str)
        assert sample_athlete.gender == "MALE"


class TestAthleteRelationships:
    """Tests de relaciones del modelo Athlete."""

    def test_athlete_kata_category_fk(self, sample_athlete, sample_category):
        """Un atleta puede tener una kata_category_id vinculada."""
        with rx.session() as session:
            athlete = session.get(Athlete, sample_athlete.id)
            athlete.kata_category_id = sample_category.id
            session.add(athlete)
            session.commit()
            session.refresh(athlete)

            assert athlete.kata_category_id == sample_category.id

    def test_athlete_kumite_category_fk(self, sample_athlete, sample_category):
        """Un atleta puede tener una kumite_category_id vinculada."""
        with rx.session() as session:
            athlete = session.get(Athlete, sample_athlete.id)
            athlete.kumite_category_id = sample_category.id
            session.add(athlete)
            session.commit()
            session.refresh(athlete)

            assert athlete.kumite_category_id == sample_category.id


# =============================================================================
# TOURNAMENT TESTS
# =============================================================================


class TestTournamentCRUD:
    """Tests de CRUD para el modelo Tournament."""

    def test_create_tournament(self, sample_tournament):
        """Un torneo creado tiene los campos correctos."""
        assert sample_tournament.id is not None
        assert sample_tournament.name == "Torneo de Prueba Kakumi"
        assert sample_tournament.venue == "Dojo Central"
        assert sample_tournament.start_date == datetime.date(2026, 6, 1)
        assert sample_tournament.end_date == datetime.date(2026, 6, 3)
        assert sample_tournament.tatami_count == 2
        assert sample_tournament.status == TournamentStatus.PLANIFICADO.value
        assert sample_tournament.is_public is True

    def test_create_tournament_defaults(self, sample_user):
        """Un torneo con mínimos campos tiene defaults correctos."""
        with rx.session() as session:
            tournament = Tournament(
                name="Torneo Minimo",
                venue="Lugar",
                start_date=datetime.date(2026, 7, 1),
                end_date=datetime.date(2026, 7, 2),
            )
            session.add(tournament)
            session.commit()
            session.refresh(tournament)

            assert tournament.tatami_count == 1  # default
            assert tournament.status == TournamentStatus.PLANIFICADO.value
            assert tournament.is_public is True

    def test_read_tournament_by_id(self, sample_tournament):
        """Se puede recuperar un torneo por ID."""
        with rx.session() as session:
            result = session.get(Tournament, sample_tournament.id)
            assert result is not None
            assert result.name == "Torneo de Prueba Kakumi"

    def test_update_tournament_status(self, sample_tournament):
        """Se puede actualizar el estado del torneo."""
        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            tournament.status = TournamentStatus.INSCRIPCION.value
            session.add(tournament)
            session.commit()
            session.refresh(tournament)

            assert tournament.status == TournamentStatus.INSCRIPCION.value

    def test_delete_tournament(self, sample_user):
        """Se puede eliminar un torneo."""
        with rx.session() as session:
            tournament = Tournament(
                name="Torneo Eliminable",
                venue="Lugar",
                start_date=datetime.date(2026, 8, 1),
                end_date=datetime.date(2026, 8, 2),
            )
            session.add(tournament)
            session.commit()
            tournament_id = tournament.id

            session.delete(tournament)
            session.commit()

            result = session.get(Tournament, tournament_id)
            assert result is None

    def test_tournament_unique_name(self, sample_tournament):
        """No se puede crear un torneo con nombre duplicado (unique)."""
        with rx.session() as session:
            duplicate = Tournament(
                name="Torneo de Prueba Kakumi",
                venue="Otro Lugar",
                start_date=datetime.date(2026, 9, 1),
                end_date=datetime.date(2026, 9, 2),
            )
            session.add(duplicate)
            with pytest.raises(Exception):
                session.commit()
            session.rollback()


class TestTournamentStatus:
    """Tests del flujo de estados del torneo según specs.md sección 6.1."""

    def test_tournament_status_values(self):
        """TournamentStatus enum tiene todos los estados del flujo."""
        assert TournamentStatus.PLANIFICADO.value == "PLANIFICADO"
        assert TournamentStatus.INSCRIPCION.value == "INSCRIPCION"
        assert TournamentStatus.VERIFICACION.value == "VERIFICACION"
        assert TournamentStatus.EN_CURSO.value == "EN_CURSO"
        assert TournamentStatus.FINALIZADO.value == "FINALIZADO"
        assert TournamentStatus.ARCHIVADO.value == "ARCHIVADO"

    def test_tournament_status_full_flow(self, sample_tournament):
        """Un torneo puede recorrer todos los estados del flujo."""
        flow = [
            TournamentStatus.INSCRIPCION.value,
            TournamentStatus.VERIFICACION.value,
            TournamentStatus.EN_CURSO.value,
            TournamentStatus.FINALIZADO.value,
            TournamentStatus.ARCHIVADO.value,
        ]
        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            for status in flow:
                tournament.status = status
                session.add(tournament)
                session.commit()
                session.refresh(tournament)
                assert tournament.status == status


class TestTournamentRelationships:
    """Tests de relaciones del modelo Tournament."""

    def test_tournament_created_by_user(self, sample_tournament, sample_user):
        """Un torneo está vinculado al usuario que lo creó."""
        assert sample_tournament.created_by_id == sample_user.id

    def test_tournament_has_categories(self, sample_tournament, sample_category):
        """Un torneo accede a sus categorías via relationship."""
        with rx.session() as session:
            tournament = session.get(Tournament, sample_tournament.id)
            assert len(tournament.categories) >= 1
            assert tournament.categories[0].name == sample_category.name


# =============================================================================
# TOURNAMENT CATEGORY TESTS
# =============================================================================


class TestTournamentCategoryCRUD:
    """Tests de CRUD para el modelo TournamentCategory."""

    def test_create_category(self, sample_category):
        """Una categoría creada tiene los campos correctos."""
        assert sample_category.id is not None
        assert sample_category.name == "Kata Individual Masculino Senior"
        assert sample_category.modality == Modality.KATA_INDIVIDUAL.value
        assert sample_category.gender == CategoryGender.MALE.value
        assert sample_category.min_age == 18
        assert sample_category.max_age == 35
        assert sample_category.competition_system == CompetitionSystem.ELIMINATION.value
        assert sample_category.bracket_size == 8
        assert sample_category.status == CategoryStatus.PENDING.value

    def test_create_kumite_category(self, sample_tournament):
        """Se puede crear una categoría Kumite con campos específicos."""
        with rx.session() as session:
            category = TournamentCategory(
                name="Kumite Individual Femenino -61kg",
                modality=Modality.KUMITE_INDIVIDUAL.value,
                gender=CategoryGender.FEMALE.value,
                min_age=18,
                max_age=35,
                competition_system=CompetitionSystem.ELIMINATION.value,
                bracket_size=16,
                tournament_id=sample_tournament.id,
                min_weight_kg=55.0,
                max_weight_kg=61.0,
                match_duration_seconds=180,
                extension_duration_seconds=60,
            )
            session.add(category)
            session.commit()
            session.refresh(category)

            assert category.modality == Modality.KUMITE_INDIVIDUAL.value
            assert category.min_weight_kg == 55.0
            assert category.max_weight_kg == 61.0
            assert category.match_duration_seconds == 180

    def test_read_category_by_id(self, sample_category):
        """Se puede recuperar una categoría por ID."""
        with rx.session() as session:
            result = session.get(TournamentCategory, sample_category.id)
            assert result is not None
            assert result.name == "Kata Individual Masculino Senior"

    def test_update_category_status(self, sample_category):
        """Se puede actualizar el estado de una categoría."""
        with rx.session() as session:
            category = session.get(TournamentCategory, sample_category.id)
            category.status = CategoryStatus.READY.value
            session.add(category)
            session.commit()
            session.refresh(category)

            assert category.status == CategoryStatus.READY.value

    def test_delete_category(self, sample_tournament):
        """Se puede eliminar una categoría."""
        with rx.session() as session:
            category = TournamentCategory(
                name="Categoria Eliminable",
                tournament_id=sample_tournament.id,
            )
            session.add(category)
            session.commit()
            category_id = category.id

            session.delete(category)
            session.commit()

            result = session.get(TournamentCategory, category_id)
            assert result is None


class TestTournamentCategoryEnums:
    """Tests de enums del modelo TournamentCategory."""

    def test_modality_enum_values(self):
        """Modality enum tiene los valores WKF correctos."""
        assert Modality.KATA_INDIVIDUAL.value == "KATA_INDIVIDUAL"
        assert Modality.KATA_TEAM.value == "KATA_TEAM"
        assert Modality.KUMITE_INDIVIDUAL.value == "KUMITE_INDIVIDUAL"
        assert Modality.KUMITE_TEAM.value == "KUMITE_TEAM"

    def test_category_gender_enum_values(self):
        """CategoryGender enum tiene los valores correctos."""
        assert CategoryGender.MALE.value == "MALE"
        assert CategoryGender.FEMALE.value == "FEMALE"
        assert CategoryGender.MIXED.value == "MIXED"

    def test_competition_system_enum_values(self):
        """CompetitionSystem enum tiene los valores correctos."""
        assert CompetitionSystem.ROUND_ROBIN.value == "ROUND_ROBIN"
        assert CompetitionSystem.ELIMINATION.value == "ELIMINATION"
        assert CompetitionSystem.DOUBLE_ELIMINATION.value == "DOUBLE_ELIMINATION"

    def test_category_status_enum_values(self):
        """CategoryStatus enum tiene los valores correctos."""
        assert CategoryStatus.PENDING.value == "PENDING"
        assert CategoryStatus.READY.value == "READY"
        assert CategoryStatus.IN_PROGRESS.value == "IN_PROGRESS"
        assert CategoryStatus.COMPLETED.value == "COMPLETED"


class TestTournamentCategoryDefaults:
    """Tests de valores por defecto de TournamentCategory."""

    def test_category_default_modality(self, sample_tournament):
        """La modalidad default es KATA_INDIVIDUAL."""
        with rx.session() as session:
            category = TournamentCategory(
                name="Default Modality",
                tournament_id=sample_tournament.id,
            )
            session.add(category)
            session.commit()
            session.refresh(category)

            assert category.modality == Modality.KATA_INDIVIDUAL.value

    def test_category_default_gender(self, sample_tournament):
        """El género default es MALE."""
        with rx.session() as session:
            category = TournamentCategory(
                name="Default Gender",
                tournament_id=sample_tournament.id,
            )
            session.add(category)
            session.commit()
            session.refresh(category)

            assert category.gender == CategoryGender.MALE.value

    def test_category_default_bracket_size(self, sample_tournament):
        """El bracket_size default es 8."""
        with rx.session() as session:
            category = TournamentCategory(
                name="Default Bracket",
                tournament_id=sample_tournament.id,
            )
            session.add(category)
            session.commit()
            session.refresh(category)

            assert category.bracket_size == 8

    def test_category_default_judge_panel_size(self, sample_tournament):
        """El judge_panel_size default es 3."""
        with rx.session() as session:
            category = TournamentCategory(
                name="Default Panel",
                tournament_id=sample_tournament.id,
            )
            session.add(category)
            session.commit()
            session.refresh(category)

            assert category.judge_panel_size == 3


class TestTournamentCategoryRelationships:
    """Tests de relaciones del modelo TournamentCategory."""

    def test_category_belongs_to_tournament(self, sample_category, sample_tournament):
        """Una categoría pertenece a un torneo via FK."""
        assert sample_category.tournament_id == sample_tournament.id

    def test_category_has_tournament_relationship(
        self, sample_category, sample_tournament
    ):
        """La relación tournament está disponible."""
        with rx.session() as session:
            category = session.get(TournamentCategory, sample_category.id)
            assert category.tournament is not None
            assert category.tournament.id == sample_tournament.id
