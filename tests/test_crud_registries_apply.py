"""Strict-TDD coverage for crud-registros-kakumi apply phase."""

from __future__ import annotations

import datetime
import importlib
import io
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest
import reflex as rx
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel.orm.session import Session as SQLModelSession
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.referee_model import Referee
from kakumi_app.services.export_service import ExportService
from kakumi_app.services.import_service import ImportService
from kakumi_app.models.tournament_model import (
    Tournament,
    TournamentStatus,
)
from kakumi_app.states.athlete_state import AthleteState
from kakumi_app.states.referee_state import RefereeState
from kakumi_app.states.tournament_state import TournamentState


def test_crud_mixin_search_and_pagination_helpers_reset_page() -> None:
    """Shared mixin helpers reset page and return bounded slices."""
    state = AthleteState()
    state.search_query = "old"
    state.current_page = 3
    state.page_size = 2

    state.apply_search_query("  dojo norte  ")
    assert state.search_query == "dojo norte"
    assert state.current_page == 1

    rows = [{"id": 1}, {"id": 2}, {"id": 3}]
    assert state.paginate_rows(rows) == [{"id": 1}, {"id": 2}]

    state.current_page = 2
    assert state.paginate_rows(rows) == [{"id": 3}]

    state.reset_filters()
    assert state.search_query == ""
    assert state.current_page == 1


def test_athlete_and_referee_derived_labels_are_human_readable() -> None:
    """Derived labels must map boolean flags to readable Spanish labels."""
    athlete_state = AthleteState()
    referee_state = RefereeState()

    assert athlete_state.athlete_status_label({"is_active": True}) == "Activo"
    assert athlete_state.athlete_status_label({"is_active": False}) == "Inactivo"

    assert (
        referee_state.referee_availability_label({"is_available": True})
        == "Disponible"
    )
    assert (
        referee_state.referee_availability_label({"is_available": False})
        == "No disponible"
    )


@pytest.mark.anyio
async def test_athlete_and_referee_route_init_loads_rows(
    sample_athlete: Athlete,
    sample_referee: Referee,
) -> None:
    """Route init handlers must reset UI flags and reload entity rows."""
    athlete_state = AthleteState()
    athlete_state.show_form = True
    athlete_state.error_message = "stale"
    athlete_state.search_query = "abc"

    await AthleteState.initialize_registry_view.fn(athlete_state)

    assert athlete_state.show_form is False
    assert athlete_state.error_message == ""
    assert athlete_state.search_query == ""
    assert any(row["id"] == sample_athlete.id for row in athlete_state.athletes)

    referee_state = RefereeState()
    referee_state.show_form = True
    referee_state.error_message = "stale"
    referee_state.search_query = "abc"

    await RefereeState.initialize_registry_view.fn(referee_state)

    assert referee_state.show_form is False
    assert referee_state.error_message == ""
    assert referee_state.search_query == ""
    assert any(row["id"] == sample_referee.id for row in referee_state.referees)


@pytest.mark.anyio
async def test_tournament_crud_delete_blocks_related_entities(
    sample_tournament: Tournament,
    sample_category: Any,
) -> None:
    """Tournament delete must be guarded when dependent rows exist."""
    from kakumi_app.states.tournament_crud_state import TournamentCrudState

    state = TournamentCrudState()

    result = await TournamentCrudState.delete_tournament.fn(state, sample_tournament.id)

    assert result is not None
    assert "No se puede eliminar" in state.error_message

    with rx.session() as session:
        still_exists = session.get(Tournament, sample_tournament.id)
        assert still_exists is not None
        assert session.exec(
            select(Tournament).where(Tournament.id == sample_tournament.id)
        ).first()

    del sample_category


@pytest.mark.anyio
async def test_tournament_crud_load_shapes_rows_as_json_safe_dicts(
    sample_tournament: Tournament,
) -> None:
    """Loaded tournament rows should be dict snapshots with string dates."""
    from kakumi_app.states.tournament_crud_state import TournamentCrudState

    state = TournamentCrudState()
    await TournamentCrudState.load_tournaments.fn(state)

    assert state.tournaments
    row = next(item for item in state.tournaments if item["id"] == sample_tournament.id)
    assert isinstance(row, dict)
    assert isinstance(row["start_date"], str)
    assert isinstance(row["end_date"], str)


@pytest.mark.anyio
async def test_tournament_crud_filter_matches_name_and_venue(
    sample_user: Any,
) -> None:
    """Tournament filter must match by name and venue semantics."""
    from kakumi_app.states.tournament_crud_state import TournamentCrudState

    with rx.session() as session:
        t1 = Tournament(
            name="Open Norte",
            venue="Dojo Azul",
            start_date=datetime.date(2027, 1, 10),
            end_date=datetime.date(2027, 1, 11),
            status=TournamentStatus.PLANIFICADO.value,
            created_by_id=sample_user.id,
        )
        t2 = Tournament(
            name="Open Sur",
            venue="Dojo Verde",
            start_date=datetime.date(2027, 2, 10),
            end_date=datetime.date(2027, 2, 11),
            status=TournamentStatus.PLANIFICADO.value,
            created_by_id=sample_user.id,
        )
        session.add(t1)
        session.add(t2)
        session.commit()

    state = TournamentCrudState()
    state.search_query = "azul"
    await TournamentCrudState.filter_tournaments.fn(state)

    assert len(state.tournaments) == 1
    assert state.tournaments[0]["name"] == "Open Norte"


@pytest.mark.anyio
async def test_tournament_crud_save_create_then_update(sample_user: Any) -> None:
    """Tournament CRUD state must create and update using form fields."""
    from kakumi_app.states.tournament_crud_state import TournamentCrudState

    state = TournamentCrudState()
    state.name = "Copa Delta"
    state.venue = "Polideportivo"
    state.start_date = "2027-03-01"
    state.end_date = "2027-03-02"
    state.tatami_count = "2"
    state.status = TournamentStatus.PLANIFICADO.value
    state.created_by_id = str(sample_user.id)

    await TournamentCrudState.save_tournament.fn(state)

    with rx.session() as session:
        created = session.exec(
            select(Tournament).where(Tournament.name == "Copa Delta")
        ).first()
        assert created is not None
        created_id = created.id

    state.is_editing = True
    state.current_tournament = {"id": created_id}
    state.venue = "Polideportivo Central"
    await TournamentCrudState.save_tournament.fn(state)

    with rx.session() as session:
        updated = session.get(Tournament, created_id)
        assert updated is not None
        assert updated.venue == "Polideportivo Central"


@pytest.mark.anyio
async def test_tournament_crud_delete_blocks_non_terminal_status(
    sample_tournament: Tournament,
) -> None:
    """Tournament delete must reject active lifecycle statuses."""
    from kakumi_app.states.tournament_crud_state import TournamentCrudState

    with rx.session() as session:
        tournament = session.get(Tournament, sample_tournament.id)
        tournament.status = TournamentStatus.EN_CURSO.value
        session.add(tournament)
        session.commit()

    state = TournamentCrudState()
    await TournamentCrudState.delete_tournament.fn(state, sample_tournament.id)

    assert "estado EN_CURSO" in state.error_message


@pytest.mark.anyio
async def test_tournament_crud_delete_allows_planificado_without_dependencies(
    sample_user: Any,
) -> None:
    """Delete should succeed for PLANIFICADO tournaments without dependencies."""
    from kakumi_app.states.tournament_crud_state import TournamentCrudState

    with rx.session() as session:
        tournament = Tournament(
            name="Delete Me",
            venue="Dojo",
            start_date=datetime.date(2027, 1, 10),
            end_date=datetime.date(2027, 1, 11),
            tatami_count=1,
            status=TournamentStatus.PLANIFICADO.value,
            created_by_id=sample_user.id,
        )
        session.add(tournament)
        session.commit()
        session.refresh(tournament)
        tournament_id = tournament.id

    state = TournamentCrudState()
    await TournamentCrudState.delete_tournament.fn(state, tournament_id)

    assert state.error_message == ""
    with rx.session() as session:
        assert session.get(Tournament, tournament_id) is None


@pytest.mark.anyio
async def test_tournament_crud_state_does_not_replace_transition_lifecycle(
    sample_tournament: Tournament,
) -> None:
    """Boundary: TournamentState transition handlers remain in dedicated state."""
    from kakumi_app.states.tournament_crud_state import TournamentCrudState

    transition_state = TournamentState()
    transition_state.current_tournament = {"id": sample_tournament.id}
    transition_state._current_user_id = 1
    transition_state._current_user_role = "ADMIN"

    assert callable(getattr(TournamentState, "start_competition", None))
    assert not hasattr(TournamentCrudState, "start_competition")


def test_registries_routes_register_crud_pages_with_on_load_handlers() -> None:
    """Registry routes must use real CRUD pages and on_load state initializers."""
    page_module = importlib.import_module("reflex.page")
    original_count = len(page_module.DECORATED_PAGES.get("kakumi_app", []))

    sys.modules.pop("kakumi_app.pages.registries", None)
    importlib.import_module("kakumi_app.pages.registries")

    new_pages = page_module.DECORATED_PAGES.get("kakumi_app", [])[original_count:]
    configs = {config.get("route"): config for _, config in new_pages}

    assert "/registries/athletes" in configs
    assert "/registries/referees" in configs
    assert "/registries/tournaments" in configs
    assert (
        configs["/registries/athletes"].get("on_load")
        == AthleteState.initialize_registry_view
    )
    assert (
        configs["/registries/referees"].get("on_load")
        == RefereeState.initialize_registry_view
    )


def test_registries_items_point_to_tournament_route_not_categories() -> None:
    """Registry cards must point tournaments card to /registries/tournaments."""
    file_content = (
        Path(__file__).resolve().parents[1]
        / "kakumi_app/components/registries_items.py"
    ).read_text(encoding="utf-8")
    assert "/registries/tournaments" in file_content
    assert "/registries/categories" not in file_content


def test_admin_alias_routes_still_registered() -> None:
    """Legacy admin athlete/referee routes must remain available as aliases."""
    import kakumi_app.kakumi_app  # noqa: F401

    page_module = importlib.import_module("reflex.page")
    pages = page_module.DECORATED_PAGES.get("kakumi_app", [])
    routes = {config.get("route") for _, config in pages}
    assert "/admin/athletes" in routes
    assert "/admin/referees" in routes


def test_admin_alias_pages_use_component_body_with_on_load_redirect() -> None:
    """Legacy alias pages must render a Component and redirect on page load."""
    page_module = importlib.import_module("reflex.page")
    original_count = len(page_module.DECORATED_PAGES.get("kakumi_app", []))

    sys.modules.pop("kakumi_app.pages.admin.athletes_page", None)
    sys.modules.pop("kakumi_app.pages.admin.referees_page", None)
    athletes_module = importlib.import_module("kakumi_app.pages.admin.athletes_page")
    referees_module = importlib.import_module("kakumi_app.pages.admin.referees_page")

    new_pages = page_module.DECORATED_PAGES.get("kakumi_app", [])[original_count:]
    configs = {config.get("route"): config for _, config in new_pages}

    assert configs["/admin/athletes"].get("on_load") is not None
    assert configs["/admin/referees"].get("on_load") is not None
    assert isinstance(athletes_module.athletes(), rx.Component)
    assert isinstance(referees_module.referees(), rx.Component)


def test_admin_alias_pages_render_non_empty_compile_safe_body() -> None:
    """Alias pages should render a real placeholder body while redirecting on_load."""
    athletes_module = importlib.import_module("kakumi_app.pages.admin.athletes_page")
    referees_module = importlib.import_module("kakumi_app.pages.admin.referees_page")

    athletes_component = athletes_module.athletes()
    referees_component = referees_module.referees()

    assert isinstance(athletes_component, rx.Component)
    assert isinstance(referees_component, rx.Component)
    assert "Redirigiendo" in str(athletes_component)
    assert "Redirigiendo" in str(referees_component)


def test_registries_page_uses_inline_labels_and_form_rendering_branches() -> None:
    """
    Registries page should avoid state helper calls in table cells and render forms.
    """
    file_content = (
        Path(__file__).resolve().parents[1] / "kakumi_app/pages/registries.py"
    ).read_text(encoding="utf-8")

    assert "athlete_status_label(" not in file_content
    assert "referee_availability_label(" not in file_content
    assert "rx.cond(state.show_form" in file_content
    assert "_athlete_form()" in file_content
    assert "_referee_form()" in file_content
    assert "_tournament_form()" in file_content


@pytest.mark.anyio
async def test_athlete_state_import_export_are_active(
    monkeypatch: pytest.MonkeyPatch,
    sample_athlete: Athlete,
) -> None:
    """Athlete import/export actions should invoke service layer and update state."""
    del sample_athlete
    state = AthleteState()
    state.import_content = "dummy"
    state.import_file_type = "csv"

    called = {"import": False, "export": False}

    def _fake_import(csv_content: str) -> tuple[int, int, list[str]]:
        called["import"] = True
        assert csv_content == "dummy"
        with rx.session() as session:
            session.add(
                Athlete(
                    name="Importado",
                    date_of_birth=datetime.date(2001, 1, 1),
                    gender="MALE",
                    is_active=True,
                )
            )
            session.commit()
        return 1, 0, []

    def _fake_export() -> str:
        called["export"] = True
        return "id,name\n1,Demo\n"

    monkeypatch.setattr(
        ImportService,
        "import_athletes_csv",
        staticmethod(_fake_import),
    )
    monkeypatch.setattr(
        ExportService,
        "export_athletes_csv",
        staticmethod(_fake_export),
    )

    await AthleteState.import_athletes.fn(state)
    assert called["import"] is True
    assert state.import_success_count == 1
    assert state.import_error_count == 0
    assert any(row["name"] == "Importado" for row in state.athletes)

    AthleteState.export_athletes.fn(state)
    assert called["export"] is True
    assert "id,name" in state.export_content


@pytest.mark.anyio
async def test_referee_state_import_export_are_active(
    monkeypatch: pytest.MonkeyPatch,
    sample_referee: Referee,
) -> None:
    """Referee import/export actions should invoke service layer and update state."""
    del sample_referee
    state = RefereeState()
    state.import_content = "dummy"
    state.import_file_type = "csv"

    called = {"import": False, "export": False}

    def _fake_import(csv_content: str) -> tuple[int, int, list[str]]:
        called["import"] = True
        assert csv_content == "dummy"
        with rx.session() as session:
            session.add(
                Referee(
                    name="Ref Importado",
                    license_number="REF-IMP-1",
                    license_level="NATIONAL",
                    role="REFEREE",
                    is_available=True,
                )
            )
            session.commit()
        return 1, 0, []

    def _fake_export() -> str:
        called["export"] = True
        return "id,name\n1,Ref\n"

    monkeypatch.setattr(
        ImportService,
        "import_referees_csv",
        staticmethod(_fake_import),
    )
    monkeypatch.setattr(
        ExportService,
        "export_referees_csv",
        staticmethod(_fake_export),
    )

    await RefereeState.import_referees.fn(state)
    assert called["import"] is True
    assert state.import_success_count == 1
    assert state.import_error_count == 0
    assert any(row["name"] == "Ref Importado" for row in state.referees)

    RefereeState.export_referees.fn(state)
    assert called["export"] is True
    assert "id,name" in state.export_content


def test_import_referees_csv_and_json_and_export_referees_csv() -> None:
    """Referee service IO should be fully implemented and non-placeholder."""
    csv_payload = io.StringIO()
    writer = csv_payload.write
    writer("name,license_number,license_level,role,is_available,dojo,email,phone\n")
    writer("Ref Uno,REF-100,NATIONAL,REFEREE,true,Dojo A,uno@test.dev,123\n")

    imported, errors, messages = ImportService.import_referees_csv(
        csv_payload.getvalue()
    )
    assert imported == 1
    assert errors == 0
    assert messages == []

    json_payload = (
        '{"referees": ['
        '{"name": "Ref Dos", "license_number": "REF-101", '
        '"license_level": "INTERNATIONAL", "role": "JUDGE", '
        '"is_available": true, "dojo": "Dojo B", '
        '"email": "dos@test.dev", "phone": "999"}]}'
    )
    imported_json, errors_json, messages_json = ImportService.import_referees_json(
        json_payload
    )
    assert imported_json == 1
    assert errors_json == 0
    assert messages_json == []

    csv_export = ExportService.export_referees_csv()
    assert "license_number" in csv_export
    assert "Ref Uno" in csv_export
    assert "Ref Dos" in csv_export


def test_registry_crud_module_exposes_screenshot_layout_primitives() -> None:
    """Shared CRUD module should expose screenshot-like layout primitives."""
    file_content = (
        Path(__file__).resolve().parents[1] / "kakumi_app/components/registry_crud.py"
    ).read_text(encoding="utf-8")

    assert "def registry_actions_header(" in file_content
    assert "def registry_table_card(" in file_content
    assert "def registry_empty_state(" in file_content
    assert "def registry_pagination_footer(" in file_content
    assert "def registry_top_bar(" not in file_content


def test_registries_page_uses_redesigned_shared_shell_components() -> None:
    """Entity pages should consume top bar, action header and table card components."""
    file_content = (
        Path(__file__).resolve().parents[1] / "kakumi_app/pages/registries.py"
    ).read_text(encoding="utf-8")

    assert "registry_actions_header(" in file_content
    assert "registry_table_card(" in file_content
    assert "registry_pagination_footer(" in file_content
    assert "registry_top_bar(" not in file_content


def test_registry_shell_has_no_duplicate_header_search_or_hamburger() -> None:
    """
    Registries UI should rely on sidebar trigger only, without extra top bar
    controls.
    """
    page_content = (
        Path(__file__).resolve().parents[1] / "kakumi_app/pages/registries.py"
    ).read_text(encoding="utf-8")
    shell_content = (
        Path(__file__).resolve().parents[1] / "kakumi_app/components/registry_crud.py"
    ).read_text(encoding="utf-8")

    assert "registry_top_bar(" not in page_content
    assert "def registry_top_bar(" not in shell_content
    assert '"☰"' not in shell_content


def test_registries_page_keeps_active_import_export_buttons_for_supported_entities(
) -> None:
    """
    Athletes/referees must keep active import and export actions in redesigned
    header.
    """
    file_content = (
        Path(__file__).resolve().parents[1] / "kakumi_app/pages/registries.py"
    ).read_text(encoding="utf-8")

    assert "Importar" in file_content
    assert "Exportar" in file_content
    assert "state.import_athletes" in file_content
    assert "state.export_athletes" in file_content
    assert "state.import_referees" in file_content
    assert "state.export_referees" in file_content


@pytest.mark.anyio
async def test_tournament_crud_save_rolls_back_and_shows_toast_on_db_error(
    monkeypatch: pytest.MonkeyPatch,
    sample_user: Any,
) -> None:
    """Tournament save should rollback and show toast on DB commit failure."""
    from kakumi_app.states import tournament_crud_state as tournament_crud_state_module
    from kakumi_app.states.tournament_crud_state import TournamentCrudState

    rollback_calls = {"count": 0}

    def _raise_commit(self) -> None:
        raise SQLAlchemyError("db down")

    def _count_rollback(self) -> None:
        rollback_calls["count"] += 1

    monkeypatch.setattr(SQLModelSession, "commit", _raise_commit)
    monkeypatch.setattr(SQLModelSession, "rollback", _count_rollback)
    monkeypatch.setattr(
        tournament_crud_state_module.rx.toast,
        "error",
        lambda msg: msg,
    )

    state = TournamentCrudState()
    state.name = "DB Error Cup"
    state.venue = "Dojo"
    state.start_date = "2027-03-01"
    state.end_date = "2027-03-02"
    state.tatami_count = "1"
    state.status = TournamentStatus.PLANIFICADO.value
    state.created_by_id = str(sample_user.id)

    result = await TournamentCrudState.save_tournament.fn(state)

    assert rollback_calls["count"] == 1
    assert isinstance(result, str)
    assert "Error al guardar torneo" in result


def test_import_athletes_csv_invalid_header_handles_missing_fieldnames() -> None:
    """Athlete CSV import must handle None fieldnames (invalid CSV) safely."""
    imported, errors, messages = ImportService.import_athletes_csv("")

    assert imported == 0
    assert errors == 1
    assert messages == ["CSV missing required fields: name, date_of_birth, gender"]


def test_import_athletes_csv_commits_once_after_processing_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Athlete CSV import should commit once after row processing."""
    commit_calls = {"count": 0}

    original_commit = SQLModelSession.commit

    def _count_commit(self) -> None:
        commit_calls["count"] += 1
        return original_commit(self)

    monkeypatch.setattr(SQLModelSession, "commit", _count_commit)

    suffix = uuid.uuid4().hex[:8]

    csv_payload = (
        "name,date_of_birth,gender,email\n"
        f"Athlete One {suffix},2001-01-01,MALE,one-{suffix}@test.dev\n"
        f"Athlete Two {suffix},2002-02-02,FEMALE,two-{suffix}@test.dev\n"
    )
    imported, errors, messages = ImportService.import_athletes_csv(csv_payload)

    assert imported == 2
    assert errors == 0
    assert messages == []
    assert commit_calls["count"] == 1


def test_import_referees_json_serializes_csv_fields_safely() -> None:
    """Referee JSON import should preserve comma-containing values."""
    json_payload = (
        '{"referees": ['
        '{"name": "Ref Tres", "license_number": "REF-JSON-3", '
        '"license_level": "NATIONAL", "role": "REFEREE", '
        '"is_available": true, "dojo": "Dojo, Norte", '
        '"email": "tres@test.dev", "phone": "777"}]}'
    )

    imported, errors, messages = ImportService.import_referees_json(json_payload)

    assert imported == 1
    assert errors == 0
    assert messages == []

    with rx.session() as session:
        stored = session.exec(
            select(Referee).where(Referee.license_number == "REF-JSON-3")
        ).first()

    assert stored is not None
    assert stored.dojo == "Dojo, Norte"


def test_parse_athlete_row_normalizes_nullable_fields_without_crashing() -> None:
    """parse_athlete_row must tolerate nullable CSV/JSON values."""
    success, data, error = ImportService.parse_athlete_row(
        {
            "name": None,
            "date_of_birth": None,
            "gender": None,
            "weight_kg": None,
            "belt_rank": None,
            "dojo": None,
            "nationality": None,
            "license_number": None,
            "email": None,
        },
        2,
    )

    assert success is False
    assert data is None
    assert "Row 2:" in error


def test_import_service_accepts_belt_colors_from_blanco_to_negro() -> None:
    """Athlete belt validator should accept belt color values."""
    valid_colors = [
        "Blanco",
        "Amarillo",
        "Naranja",
        "Verde",
        "Azul",
        "Marron",
        "Negro",
    ]

    for color in valid_colors:
        assert ImportService.validate_belt_rank(color) is True


def test_parse_athlete_row_accepts_belt_color() -> None:
    """Athlete parse should accept color-based belt rank value."""
    success, data, error = ImportService.parse_athlete_row(
        {
            "name": "Color Belt",
            "date_of_birth": "2002-03-04",
            "gender": "MALE",
            "weight_kg": "72",
            "belt_rank": "Verde",
            "dojo": "Dojo Norte",
            "nationality": "ARG",
        },
        3,
    )

    assert success is True
    assert error == ""
    assert data is not None
    assert data["belt_rank"] == "Verde"
