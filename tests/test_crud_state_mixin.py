"""Batch 4 CRUD mixin tests (strict TDD)."""

from __future__ import annotations

import inspect
from datetime import date

import pytest
import reflex as rx
from reflex.event import EventHandler
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.referee_model import Referee
from kakumi_app.models.team_model import Team
from kakumi_app.states.athlete_state import AthleteState
from kakumi_app.states.base_crud_state import CrudStateMixin
from kakumi_app.states.referee_state import RefereeState
from kakumi_app.states.team_state import TeamState


@pytest.mark.parametrize("state_cls", [AthleteState, RefereeState, TeamState])
def test_mixin_mro_and_shared_default_vars(state_cls: type) -> None:
    """Child states must use mixin MRO and shared defaults."""
    mro = state_cls.__mro__
    assert CrudStateMixin in mro
    assert rx.State in mro
    assert mro.index(CrudStateMixin) < mro.index(rx.State)

    state = state_cls()
    assert state.is_editing is False
    assert state.show_form is False
    assert state.error_message == ""
    assert state.search_query == ""


def test_crud_mixin_stays_pure_python_not_rx_state_subclass() -> None:
    """Mixin must be rx.State-free to avoid Reflex inheritance hazards."""
    assert issubclass(CrudStateMixin, rx.State) is False


@pytest.mark.parametrize("state_cls", [AthleteState, RefereeState, TeamState])
def test_cancel_form_keeps_edit_mode_and_clears_ui_flags(state_cls: type) -> None:
    """cancel_form keeps is_editing and clears shared UI flags."""
    state = state_cls()
    state.is_editing = True
    state.show_form = True
    state.error_message = "validation error"

    state.cancel_form()

    assert state.is_editing is True
    assert state.show_form is False
    assert state.error_message == ""


@pytest.mark.parametrize("editing", [True, False])
def test_set_form_open_sets_show_form_edit_mode_and_clears_error(
    editing: bool,
) -> None:
    """Helper must open form, sync edit mode and clear stale errors."""
    state = AthleteState()
    state.show_form = False
    state.error_message = "old error"

    state._set_form_open(editing=editing)

    assert state.show_form is True
    assert state.is_editing is editing
    assert state.error_message == ""


def test_athlete_set_form_values_edit_populates_fields_and_flags() -> None:
    """Athlete edit path must preserve existing population behavior."""
    athlete = {
        "id": 17,
        "name": "Atleta Edit",
        "date_of_birth": "2002-07-01",
        "gender": "FEMALE",
        "email": "athlete@test.dev",
        "weight_kg": 62.5,
        "belt_rank": "Dan 2",
        "dojo": "Dojo Sur",
        "nationality": "ARG",
        "license_number": "A-001",
        "is_active": False,
    }
    state = AthleteState()

    AthleteState.set_form_values.fn(state, None, athlete)

    assert state.current_athlete["id"] == athlete["id"]
    assert state.is_editing is True
    assert state.show_form is True
    assert state.error_message == ""
    assert state.name == "Atleta Edit"
    assert state.date_of_birth == "2002-07-01"
    assert state.gender == "FEMALE"
    assert state.weight_kg == "62.5"
    assert state.belt_rank == "Dan 2"
    assert state.dojo == "Dojo Sur"
    assert state.nationality == "ARG"
    assert state.license_number == "A-001"
    assert state.is_active is False


def test_athlete_set_form_values_create_resets_fields() -> None:
    """Athlete create path must reset form and open non-edit mode."""
    state = AthleteState()
    state.current_athlete = {"id": 8, "name": "Old"}
    state.name = "Dirty"
    state.date_of_birth = "2020-01-01"
    state.gender = "FEMALE"
    state.weight_kg = "80"
    state.error_message = "old"

    AthleteState.set_form_values.fn(state, None, None)

    assert state.current_athlete is None
    assert state.is_editing is False
    assert state.show_form is True
    assert state.error_message == ""
    assert state.name == ""
    assert state.date_of_birth == ""
    assert state.gender == "MALE"
    assert state.weight_kg == ""


def test_referee_set_form_values_edit_populates_fields_and_flags() -> None:
    """Referee edit path keeps field mapping stable."""
    referee = {
        "id": 21,
        "name": "Ref Edit",
        "license_number": "REF-009",
        "license_level": "INTERNATIONAL",
        "role": "JUDGE",
        "tatami_certified": '["A", "B"]',
        "is_available": False,
        "dojo": "Federación",
        "email": "ref@test.dev",
        "phone": "12345",
    }
    state = RefereeState()

    RefereeState.set_form_values.fn(state, None, referee)

    assert state.current_referee["id"] == referee["id"]
    assert state.is_editing is True
    assert state.show_form is True
    assert state.error_message == ""
    assert state.name == "Ref Edit"
    assert state.license_number == "REF-009"
    assert state.license_level == "INTERNATIONAL"
    assert state.role == "JUDGE"
    assert state.tatami_certified == '["A", "B"]'
    assert state.is_available is False
    assert state.dojo == "Federación"
    assert state.email == "ref@test.dev"
    assert state.phone == "12345"


def test_referee_set_form_values_create_resets_fields() -> None:
    """Referee create path resets form values and opens non-edit mode."""
    state = RefereeState()
    state.current_referee = {"id": 33, "name": "Ref"}
    state.name = "Dirty"
    state.license_number = "DIRTY"
    state.license_level = "INTERNATIONAL"
    state.error_message = "old"

    RefereeState.set_form_values.fn(state, None, None)

    assert state.current_referee is None
    assert state.is_editing is False
    assert state.show_form is True
    assert state.error_message == ""
    assert state.name == ""
    assert state.license_number == ""
    assert state.license_level == "NATIONAL"
    assert state.role == "REFEREE"


def test_team_set_form_values_edit_populates_fields_and_flags() -> None:
    """Team edit path keeps category and flags behavior stable."""
    team = {
        "id": 40,
        "name": "Team Edit",
        "category_id": 12,
        "dojo": "Dojo Oeste",
        "member_count": 0,
        "is_active": False,
    }
    state = TeamState()

    TeamState.set_form_values.fn(state, None, team)

    assert state.current_team["id"] == team["id"]
    assert state.is_editing is True
    assert state.show_form is True
    assert state.error_message == ""
    assert state.name == "Team Edit"
    assert state.category_id == "12"
    assert state.dojo == "Dojo Oeste"
    assert state.is_active is False


def test_team_set_form_values_create_resets_fields() -> None:
    """Team create path resets state and opens form in create mode."""
    state = TeamState()
    state.current_team = {"id": 41, "name": "Old", "category_id": 2}
    state.name = "Dirty"
    state.category_id = "999"
    state.dojo = "Dirty Dojo"
    state.error_message = "old"

    TeamState.set_form_values.fn(state, None, None)

    assert state.current_team is None
    assert state.is_editing is False
    assert state.show_form is True
    assert state.error_message == ""
    assert state.name == ""
    assert state.category_id == ""
    assert state.dojo == ""


@pytest.mark.anyio
async def test_filter_athletes_applies_case_insensitive_name_email_dojo_match(
    sample_athlete: Athlete,
) -> None:
    """Athlete filter must match by name/email/dojo with lowercase query."""
    with rx.session() as session:
        athlete_match = Athlete(
            name="Luna Karate",
            date_of_birth=date(2001, 5, 1),
            gender="FEMALE",
            email="luna.filter@test.dev",
            dojo="Dojo Norte",
        )
        athlete_non_match = Athlete(
            name="Pedro Sur",
            date_of_birth=date(2000, 2, 2),
            gender="MALE",
            email="pedro@test.dev",
            dojo="Dojo Sur",
        )
        session.add(athlete_match)
        session.add(athlete_non_match)
        session.commit()

    state = AthleteState()
    state.search_query = "nOrTe"

    await AthleteState.filter_athletes.fn(state)

    assert len(state.athletes) == 1
    assert isinstance(state.athletes[0], dict)
    assert state.athletes[0]["name"] == "Luna Karate"
    assert state.athletes[0]["id"] != sample_athlete.id


@pytest.mark.anyio
async def test_filter_athletes_without_query_reloads_all_rows(
    sample_athlete: Athlete,
) -> None:
    """Athlete filter with empty query must reload full list."""
    with rx.session() as session:
        second = Athlete(
            name="Atleta Dos",
            date_of_birth=date(2002, 1, 10),
            gender="MALE",
            email="atleta2@test.dev",
        )
        session.add(second)
        session.commit()
        session.refresh(second)

    state = AthleteState()
    state.search_query = ""

    await AthleteState.filter_athletes.fn(state)

    assert all(isinstance(athlete, dict) for athlete in state.athletes)
    athlete_ids = {athlete["id"] for athlete in state.athletes}
    assert sample_athlete.id in athlete_ids
    assert second.id in athlete_ids


@pytest.mark.anyio
async def test_filter_referees_matches_license_email_and_dojo(
    sample_referee: Referee,
) -> None:
    """Referee filter must include license/email/dojo search semantics."""
    with rx.session() as session:
        referee_match = Referee(
            name="Panel Norte",
            license_number="FILTRO-777",
            license_level="NATIONAL",
            role="JUDGE",
            dojo="Zona Centro",
            email="panel@test.dev",
            is_available=True,
        )
        referee_non_match = Referee(
            name="Mesa Sur",
            license_number="SUR-001",
            license_level="NATIONAL",
            role="REFEREE",
            dojo="Zona Sur",
            email="sur@test.dev",
            is_available=True,
        )
        session.add(referee_match)
        session.add(referee_non_match)
        session.commit()

    state = RefereeState()
    state.search_query = "filtro-777"

    await RefereeState.filter_referees.fn(state)

    assert len(state.referees) == 1
    assert isinstance(state.referees[0], dict)
    assert state.referees[0]["license_number"] == "FILTRO-777"
    assert state.referees[0]["id"] != sample_referee.id


@pytest.mark.anyio
async def test_filter_referees_without_query_reloads_all_rows(
    sample_referee: Referee,
) -> None:
    """Referee filter with empty query must reload full list."""
    with rx.session() as session:
        second = Referee(
            name="Second Ref",
            license_number="REF-SECOND-01",
            license_level="INTERNATIONAL",
            role="JUDGE",
            email="second-ref@test.dev",
            is_available=True,
        )
        session.add(second)
        session.commit()
        session.refresh(second)

    state = RefereeState()
    state.search_query = ""

    await RefereeState.filter_referees.fn(state)

    assert all(isinstance(referee, dict) for referee in state.referees)
    referee_ids = {referee["id"] for referee in state.referees}
    assert sample_referee.id in referee_ids
    assert second.id in referee_ids


@pytest.mark.anyio
async def test_filter_teams_matches_name_and_dojo(sample_team: Team) -> None:
    """Team filter must match by team name and dojo fields."""
    with rx.session() as session:
        team_match = Team(
            name="Norte Squad",
            category_id=sample_team.category_id,
            member_count=0,
            is_active=True,
            dojo="Dojo Delta",
        )
        team_non_match = Team(
            name="Sur Squad",
            category_id=sample_team.category_id,
            member_count=0,
            is_active=True,
            dojo="Dojo Sur",
        )
        session.add(team_match)
        session.add(team_non_match)
        session.commit()

    state = TeamState()
    state.search_query = "delta"

    await TeamState.filter_teams.fn(state)

    assert len(state.teams) == 1
    assert isinstance(state.teams[0], dict)
    assert state.teams[0]["name"] == "Norte Squad"
    assert state.teams[0]["id"] != sample_team.id


@pytest.mark.anyio
async def test_filter_teams_without_query_reloads_all_rows(sample_team: Team) -> None:
    """Team filter with empty query must reload full list."""
    with rx.session() as session:
        second = Team(
            name="Team Reload",
            category_id=sample_team.category_id,
            member_count=0,
            is_active=True,
            dojo="Dojo Reload",
        )
        session.add(second)
        session.commit()
        session.refresh(second)

    state = TeamState()
    state.search_query = ""

    await TeamState.filter_teams.fn(state)

    assert all(isinstance(team, dict) for team in state.teams)
    team_ids = {team["id"] for team in state.teams}
    assert sample_team.id in team_ids
    assert second.id in team_ids


def test_initialize_new_team_form_calls_shared_create_flow() -> None:
    """Boundary: keep initialize_new_team_form delegating to set_form_values."""
    state = TeamState()
    state.current_team = {"id": 9, "name": "Old Team", "category_id": 1}
    state.name = "Dirty"
    state.category_id = "22"
    state.error_message = "stale"
    state.show_form = False

    TeamState.initialize_new_team_form.fn(state)

    assert state.current_team is None
    assert state.name == ""
    assert state.category_id == ""
    assert state.show_form is True
    assert state.is_editing is False
    assert state.error_message == ""


@pytest.mark.anyio
async def test_save_athlete_update_rehydrates_by_current_athlete_id(
    sample_athlete: Athlete,
) -> None:
    """Update path must rehydrate from current_athlete['id'] and mutate row."""
    state = AthleteState()
    state.is_editing = True
    state.current_athlete = {"id": str(sample_athlete.id), "name": "snapshot-stale"}
    state.name = "Carlos Actualizado"
    state.email = "carlos.updated@test.dev"
    state.date_of_birth = "1998-05-15"
    state.gender = "MALE"
    state.weight_kg = "73"
    state.belt_rank = "Dan 3"
    state.dojo = "Dojo Norte"
    state.nationality = "ARG"
    state.license_number = "LIC-001-UPD"
    state.is_active = True

    await AthleteState.save_athlete.fn(state)

    with rx.session() as session:
        updated = session.get(Athlete, sample_athlete.id)
        assert updated is not None
        assert updated.name == "Carlos Actualizado"
        assert updated.email == "carlos.updated@test.dev"
        assert updated.belt_rank == "Dan 3"
        assert updated.license_number == "LIC-001-UPD"
        assert session.exec(select(Athlete)).all()
        assert len(session.exec(select(Athlete)).all()) == 1

    assert state.show_form is False
    assert state.athletes
    assert all(isinstance(athlete, dict) for athlete in state.athletes)
    assert state.athletes[0]["id"] == sample_athlete.id
    assert state.athletes[0]["name"] == "Carlos Actualizado"


@pytest.mark.anyio
async def test_save_referee_update_rehydrates_by_current_referee_id(
    sample_referee: Referee,
) -> None:
    """Update path must rehydrate from current_referee['id'] and mutate row."""
    state = RefereeState()
    state.is_editing = True
    state.current_referee = {"id": str(sample_referee.id), "name": "snapshot-stale"}
    state.name = "Referee Actualizado"
    state.license_number = "REF-001"
    state.license_level = "INTERNATIONAL"
    state.role = "JUDGE"
    state.tatami_certified = '["A"]'
    state.is_available = False
    state.dojo = "Dojo Centro"
    state.email = "ref.updated@test.dev"
    state.phone = "555-0101"

    await RefereeState.save_referee.fn(state)

    with rx.session() as session:
        updated = session.get(Referee, sample_referee.id)
        assert updated is not None
        assert updated.name == "Referee Actualizado"
        assert updated.role == "JUDGE"
        assert updated.email == "ref.updated@test.dev"
        assert updated.is_available is False
        assert len(session.exec(select(Referee)).all()) == 1

    assert state.show_form is False
    assert state.referees
    assert all(isinstance(referee, dict) for referee in state.referees)
    assert state.referees[0]["id"] == sample_referee.id
    assert state.referees[0]["name"] == "Referee Actualizado"


@pytest.mark.anyio
async def test_save_team_update_rehydrates_by_current_team_id(
    sample_team: Team,
) -> None:
    """Update path must rehydrate from current_team['id'] and mutate row."""
    state = TeamState()
    state.is_editing = True
    state.current_team = {"id": str(sample_team.id), "name": "snapshot-stale"}
    state.name = "Equipo Actualizado"
    state.category_id = str(sample_team.category_id)
    state.dojo = "Dojo Actualizado"
    state.is_active = False

    await TeamState.save_team.fn(state)

    with rx.session() as session:
        updated = session.get(Team, sample_team.id)
        assert updated is not None
        assert updated.name == "Equipo Actualizado"
        assert updated.dojo == "Dojo Actualizado"
        assert updated.is_active is False
        assert updated.category_id == sample_team.category_id
        assert len(session.exec(select(Team)).all()) == 1

    assert state.show_form is False
    assert state.teams
    assert all(isinstance(team, dict) for team in state.teams)
    assert state.teams[0]["id"] == sample_team.id
    assert state.teams[0]["name"] == "Equipo Actualizado"


def test_batch5_scope_contract_keeps_target_table_columns_stable() -> None:
    """Static contract: batch scope must not mutate target DB schema."""
    assert {column.name for column in Athlete.__table__.columns} == {
        "id",
        "name",
        "date_of_birth",
        "gender",
        "email",
        "weight_kg",
        "belt_rank",
        "dojo",
        "nationality",
        "license_number",
        "is_active",
        "is_disqualified",
        "kata_category_id",
        "kumite_category_id",
        "created_at",
        "updated_at",
    }
    assert {column.name for column in Referee.__table__.columns} == {
        "id",
        "name",
        "license_number",
        "license_level",
        "role",
        "is_available",
        "tatami_certified",
        "dojo",
        "email",
        "phone",
        "created_at",
        "updated_at",
    }
    assert {column.name for column in Team.__table__.columns} == {
        "id",
        "name",
        "category_id",
        "member_count",
        "is_active",
        "dojo",
        "created_at",
    }


@pytest.mark.parametrize(
    ("state_cls", "method_name"),
    [
        (AthleteState, "save_athlete"),
        (AthleteState, "delete_athlete"),
        (RefereeState, "save_referee"),
        (RefereeState, "delete_referee"),
        (TeamState, "save_team"),
        (TeamState, "delete_team"),
    ],
)
def test_boundary_db_event_handlers_remain_async(
    state_cls: type,
    method_name: str,
) -> None:
    """Boundary: no ORM contract rewrites in batch scope."""
    handler = getattr(state_cls, method_name)
    assert isinstance(handler, EventHandler)
    assert inspect.iscoroutinefunction(handler.fn)
