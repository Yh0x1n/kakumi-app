"""
KAKUMI Tests - Modelos de Equipo y Usuarios
=============================================
Tests para: Team, TeamMember, Referee, User
Cubre: CRUD, relaciones, enums, validaciones de campos.
"""

import datetime

import pytest
import reflex as rx
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.referee_model import (
    LicenseLevel,
    Referee,
    RefereeRole,
)
from kakumi_app.models.team_model import Team, TeamMember
from kakumi_app.models.user_model import User, UserRole


# =============================================================================
# TEAM TESTS
# =============================================================================


class TestTeamCRUD:
    """Tests de CRUD para el modelo Team."""

    def test_create_team(self, sample_team):
        """Un equipo creado tiene los campos correctos."""
        assert sample_team.id is not None
        assert sample_team.name == "Equipo Dojo Shoto"
        assert sample_team.member_count == 0
        assert sample_team.is_active is True
        assert sample_team.dojo == "Dojo Shoto"

    def test_create_team_defaults(self, sample_category):
        """Un equipo con mínimos campos tiene defaults correctos."""
        with rx.session() as session:
            team = Team(
                name="Equipo Minimo",
                category_id=sample_category.id,
            )
            session.add(team)
            session.commit()
            session.refresh(team)

            assert team.member_count == 0  # default
            assert team.is_active is True  # default
            assert team.dojo is None

    def test_read_team_by_id(self, sample_team):
        """Se puede recuperar un equipo por ID."""
        with rx.session() as session:
            result = session.get(Team, sample_team.id)
            assert result is not None
            assert result.name == "Equipo Dojo Shoto"

    def test_update_team(self, sample_team):
        """Se puede actualizar un equipo."""
        with rx.session() as session:
            team = session.get(Team, sample_team.id)
            team.member_count = 5
            team.is_active = False
            session.add(team)
            session.commit()
            session.refresh(team)

            assert team.member_count == 5
            assert team.is_active is False

    def test_delete_team(self, sample_category):
        """Se puede eliminar un equipo."""
        with rx.session() as session:
            team = Team(
                name="Equipo Eliminable",
                category_id=sample_category.id,
            )
            session.add(team)
            session.commit()
            team_id = team.id

            session.delete(team)
            session.commit()

            result = session.get(Team, team_id)
            assert result is None


class TestTeamRelationships:
    """Tests de relaciones del modelo Team."""

    def test_team_belongs_to_category(self, sample_team, sample_category):
        """Un equipo pertenece a una categoría."""
        assert sample_team.category_id == sample_category.id


# =============================================================================
# TEAM MEMBER TESTS
# =============================================================================


class TestTeamMemberCRUD:
    """Tests de CRUD para el modelo TeamMember."""

    def test_create_team_member(self, sample_team, sample_athlete):
        """Se puede crear un miembro de equipo."""
        with rx.session() as session:
            member = TeamMember(
                team_id=sample_team.id,
                athlete_id=sample_athlete.id,
                position=1,
                is_reserve=False,
            )
            session.add(member)
            session.commit()
            session.refresh(member)

            assert member.id is not None
            assert member.team_id == sample_team.id
            assert member.athlete_id == sample_athlete.id
            assert member.position == 1
            assert member.is_reserve is False

    def test_create_team_member_defaults(self, sample_team, sample_athlete):
        """Un TeamMember tiene defaults correctos."""
        with rx.session() as session:
            member = TeamMember(
                team_id=sample_team.id,
                athlete_id=sample_athlete.id,
            )
            session.add(member)
            session.commit()
            session.refresh(member)

            assert member.position == 1  # default
            assert member.is_reserve is False  # default

    def test_create_reserve_member(self, sample_team, sample_athlete_2):
        """Se puede crear un miembro reserva."""
        with rx.session() as session:
            member = TeamMember(
                team_id=sample_team.id,
                athlete_id=sample_athlete_2.id,
                position=4,
                is_reserve=True,
            )
            session.add(member)
            session.commit()
            session.refresh(member)

            assert member.is_reserve is True
            assert member.position == 4

    def test_read_team_member(self, sample_team, sample_athlete):
        """Se puede recuperar un miembro por ID."""
        with rx.session() as session:
            member = TeamMember(
                team_id=sample_team.id,
                athlete_id=sample_athlete.id,
            )
            session.add(member)
            session.commit()
            member_id = member.id

            result = session.get(TeamMember, member_id)
            assert result is not None
            assert result.team_id == sample_team.id

    def test_delete_team_member(self, sample_team, sample_athlete):
        """Se puede eliminar un miembro de equipo."""
        with rx.session() as session:
            member = TeamMember(
                team_id=sample_team.id,
                athlete_id=sample_athlete.id,
            )
            session.add(member)
            session.commit()
            member_id = member.id

            session.delete(member)
            session.commit()

            result = session.get(TeamMember, member_id)
            assert result is None


class TestTeamMemberRelationships:
    """Tests de relaciones del modelo TeamMember."""

    def test_member_belongs_to_team(self, sample_team, sample_athlete):
        """Un miembro pertenece a un equipo."""
        with rx.session() as session:
            member = TeamMember(
                team_id=sample_team.id,
                athlete_id=sample_athlete.id,
            )
            session.add(member)
            session.commit()

            assert member.team_id == sample_team.id

    def test_member_has_athlete(self, sample_team, sample_athlete):
        """Un miembro está vinculado a un atleta."""
        with rx.session() as session:
            member = TeamMember(
                team_id=sample_team.id,
                athlete_id=sample_athlete.id,
            )
            session.add(member)
            session.commit()

            assert member.athlete_id == sample_athlete.id

    def test_multiple_members_in_team(
        self, sample_team, sample_athlete, sample_athlete_2
    ):
        """Un equipo puede tener múltiples miembros."""
        with rx.session() as session:
            member1 = TeamMember(
                team_id=sample_team.id,
                athlete_id=sample_athlete.id,
                position=1,
            )
            member2 = TeamMember(
                team_id=sample_team.id,
                athlete_id=sample_athlete_2.id,
                position=2,
            )
            session.add(member1)
            session.add(member2)
            session.commit()

            query = select(TeamMember).where(TeamMember.team_id == sample_team.id)
            members = session.exec(query).all()
            assert len(members) == 2


# =============================================================================
# REFEREE TESTS
# =============================================================================


class TestRefereeCRUD:
    """Tests de CRUD para el modelo Referee."""

    def test_create_referee(self, sample_referee):
        """Un árbitro creado tiene los campos correctos."""
        assert sample_referee.id is not None
        assert sample_referee.name == "Juez Principal"
        assert sample_referee.license_number == "REF-001"
        assert sample_referee.license_level == LicenseLevel.INTERNATIONAL.value
        assert sample_referee.role == RefereeRole.REFEREE.value
        assert sample_referee.is_available is True

    def test_create_referee_defaults(self):
        """Un árbitro con mínimos campos tiene defaults correctos."""
        with rx.session() as session:
            referee = Referee(
                name="Juez Default",
                license_number="REF-DEFAULT-001",
            )
            session.add(referee)
            session.commit()
            session.refresh(referee)

            assert referee.license_level == LicenseLevel.NATIONAL.value  # default
            assert referee.role == RefereeRole.REFEREE.value  # default
            assert referee.is_available is True  # default
            assert referee.dojo is None
            assert referee.email is None

    def test_read_referee_by_id(self, sample_referee):
        """Se puede recuperar un árbitro por ID."""
        with rx.session() as session:
            result = session.get(Referee, sample_referee.id)
            assert result is not None
            assert result.name == "Juez Principal"

    def test_read_referee_by_license(self, sample_referee):
        """Se puede buscar un árbitro por número de licencia."""
        with rx.session() as session:
            query = select(Referee).where(Referee.license_number == "REF-001")
            result = session.exec(query).first()
            assert result is not None
            assert result.id == sample_referee.id

    def test_update_referee(self, sample_referee):
        """Se puede actualizar un árbitro."""
        with rx.session() as session:
            referee = session.get(Referee, sample_referee.id)
            referee.role = RefereeRole.JUDGE.value
            referee.is_available = False
            session.add(referee)
            session.commit()
            session.refresh(referee)

            assert referee.role == RefereeRole.JUDGE.value
            assert referee.is_available is False

    def test_delete_referee(self):
        """Se puede eliminar un árbitro."""
        with rx.session() as session:
            referee = Referee(
                name="Juez Eliminable",
                license_number="REF-DELETE-001",
            )
            session.add(referee)
            session.commit()
            referee_id = referee.id

            session.delete(referee)
            session.commit()

            result = session.get(Referee, referee_id)
            assert result is None

    def test_referee_duplicate_license_allowed(self, sample_referee):
        """Se permite crear árbitros con el mismo número de licencia."""
        with rx.session() as session:
            duplicate = Referee(
                name="Otro Juez",
                license_number="REF-001",
            )
            session.add(duplicate)
            session.commit()
            assert duplicate.id is not None


class TestRefereeEnums:
    """Tests de enums del modelo Referee."""

    def test_license_level_enum_values(self):
        """LicenseLevel enum tiene los valores correctos."""
        assert LicenseLevel.NATIONAL.value == "NATIONAL"
        assert LicenseLevel.INTERNATIONAL.value == "INTERNATIONAL"

    def test_referee_role_enum_values(self):
        """RefereeRole enum tiene todos los roles WKF."""
        assert RefereeRole.REFEREE.value == "REFEREE"
        assert RefereeRole.JUDGE.value == "JUDGE"
        assert RefereeRole.TABLE_OFFICIAL.value == "TABLE_OFFICIAL"
        assert RefereeRole.SUPERVISOR.value == "SUPERVISOR"

    def test_create_judge_referee(self):
        """Se puede crear un árbitro con rol JUDGE."""
        with rx.session() as session:
            referee = Referee(
                name="Juez de Mesa",
                license_number="REF-JUDGE-001",
                role=RefereeRole.JUDGE.value,
                license_level=LicenseLevel.INTERNATIONAL.value,
            )
            session.add(referee)
            session.commit()
            session.refresh(referee)

            assert referee.role == RefereeRole.JUDGE.value

    def test_create_table_official_referee(self):
        """Se puede crear un árbitro con rol TABLE_OFFICIAL."""
        with rx.session() as session:
            referee = Referee(
                name="Oficial de Mesa",
                license_number="REF-TO-001",
                role=RefereeRole.TABLE_OFFICIAL.value,
            )
            session.add(referee)
            session.commit()
            session.refresh(referee)

            assert referee.role == RefereeRole.TABLE_OFFICIAL.value


# =============================================================================
# USER TESTS
# =============================================================================


class TestUserCRUD:
    """Tests de CRUD para el modelo User."""

    def test_create_user(self, sample_user):
        """Un usuario creado tiene los campos correctos."""
        assert sample_user.id is not None
        assert sample_user.username == "test_admin"
        assert sample_user.email == "admin@kakumi.test"
        assert sample_user.password_hash == "hashed_password_123"
        assert sample_user.full_name == "Test Admin User"
        assert sample_user.role == UserRole.ADMIN.value
        assert sample_user.is_active is True

    def test_create_user_defaults(self):
        """Un usuario con mínimos campos tiene defaults correctos."""
        with rx.session() as session:
            user = User(
                username="viewer_user",
                email="viewer@kakumi.test",
                password_hash="hashed_viewer",
                full_name="Viewer User",
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            assert user.role == UserRole.OPERATOR.value  # default
            assert user.is_active is True  # default
            assert user.last_login is None

    def test_read_user_by_id(self, sample_user):
        """Se puede recuperar un usuario por ID."""
        with rx.session() as session:
            result = session.get(User, sample_user.id)
            assert result is not None
            assert result.username == "test_admin"

    def test_read_user_by_username(self, sample_user):
        """Se puede buscar un usuario por username."""
        with rx.session() as session:
            query = select(User).where(User.username == "test_admin")
            result = session.exec(query).first()
            assert result is not None
            assert result.id == sample_user.id

    def test_read_user_by_email(self, sample_user):
        """Se puede buscar un usuario por email."""
        with rx.session() as session:
            query = select(User).where(User.email == "admin@kakumi.test")
            result = session.exec(query).first()
            assert result is not None
            assert result.id == sample_user.id

    def test_update_user(self, sample_user):
        """Se puede actualizar un usuario."""
        with rx.session() as session:
            user = session.get(User, sample_user.id)
            user.full_name = "Updated Admin"
            user.role = UserRole.OPERATOR.value
            session.add(user)
            session.commit()
            session.refresh(user)

            assert user.full_name == "Updated Admin"
            assert user.role == UserRole.OPERATOR.value

    def test_update_last_login(self, sample_user):
        """Se puede actualizar last_login."""
        with rx.session() as session:
            user = session.get(User, sample_user.id)
            now = datetime.datetime.utcnow()
            user.last_login = now
            session.add(user)
            session.commit()
            session.refresh(user)

            assert user.last_login is not None

    def test_delete_user(self):
        """Se puede eliminar un usuario."""
        with rx.session() as session:
            user = User(
                username="deletable_user",
                email="deletable@kakumi.test",
                password_hash="hash",
                full_name="Deletable",
            )
            session.add(user)
            session.commit()
            user_id = user.id

            session.delete(user)
            session.commit()

            result = session.get(User, user_id)
            assert result is None

    def test_user_unique_username(self, sample_user):
        """No se puede crear un usuario con username duplicado (unique)."""
        with rx.session() as session:
            duplicate = User(
                username="test_admin",
                email="other@kakumi.test",
                password_hash="hash",
                full_name="Duplicate",
            )
            session.add(duplicate)
            with pytest.raises(Exception):
                session.commit()
            session.rollback()

    def test_user_unique_email(self, sample_user):
        """No se puede crear un usuario con email duplicado (unique)."""
        with rx.session() as session:
            duplicate = User(
                username="other_user",
                email="admin@kakumi.test",
                password_hash="hash",
                full_name="Duplicate Email",
            )
            session.add(duplicate)
            with pytest.raises(Exception):
                session.commit()
            session.rollback()


class TestUserRoles:
    """Tests de roles de usuario."""

    def test_user_role_enum_values(self):
        """UserRole enum tiene los valores correctos."""
        assert UserRole.ADMIN.value == "ADMIN"
        assert UserRole.OPERATOR.value == "OPERATOR"
        assert UserRole.VIEWER.value == "VIEWER"

    def test_create_admin_user(self):
        """Se puede crear un usuario con rol ADMIN."""
        with rx.session() as session:
            user = User(
                username="admin_role",
                email="admin_role@kakumi.test",
                password_hash="hash",
                full_name="Admin Role",
                role=UserRole.ADMIN.value,
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            assert user.role == UserRole.ADMIN.value

    def test_create_viewer_user(self):
        """Se puede crear un usuario con rol VIEWER."""
        with rx.session() as session:
            user = User(
                username="viewer_role",
                email="viewer_role@kakumi.test",
                password_hash="hash",
                full_name="Viewer Role",
                role=UserRole.VIEWER.value,
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            assert user.role == UserRole.VIEWER.value


class TestUserRelationships:
    """Tests de relaciones del modelo User."""

    def test_user_can_create_tournaments(self, sample_user, sample_tournament):
        """Un usuario accede a los torneos que creó via relationship."""
        with rx.session() as session:
            user = session.get(User, sample_user.id)
            assert len(user.created_tournaments) >= 1
            assert user.created_tournaments[0].id == sample_tournament.id
