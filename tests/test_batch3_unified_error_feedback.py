"""Batch 3 unified error feedback tests (strict TDD)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import pytest
import reflex as rx
from reflex.event import EventSpec
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.referee_model import Referee
from kakumi_app.models.team_model import Team
from kakumi_app.states.athlete_state import AthleteState
from kakumi_app.states.auth_state import AuthState
from kakumi_app.states.export_state import ExportState
from kakumi_app.states.import_state import ImportState
from kakumi_app.states.referee_state import RefereeState
from kakumi_app.states.team_state import TeamState
from kakumi_app.states.tournament_state import TournamentState
from kakumi_app.states.viewer_state import ViewerState


ROOT = Path(__file__).resolve().parents[1]


def _as_event_list(result: object) -> list[EventSpec]:
    """Normalize handler result into list of EventSpec instances."""
    if result is None:
        return []
    if isinstance(result, EventSpec):
        return [result]
    if isinstance(result, (tuple, list)):
        return [event for event in result if isinstance(event, EventSpec)]
    return []


def _event_args_map(event: EventSpec) -> dict[str, object]:
    """Build argument map from Reflex event arg tuples."""
    args_map: dict[str, object] = {}
    for key_var, value in event.args:
        key = getattr(key_var, "_js_expr", "")
        if isinstance(key, str) and key:
            args_map[key] = value
    return args_map


def _is_toast_event(event: EventSpec, toast_kind: str | None = None) -> bool:
    """Check whether event is toast, optionally by kind."""
    args_map = _event_args_map(event)
    function_arg = args_map.get("function")
    function_expr = getattr(function_arg, "_js_expr", "")
    if "__toast" not in function_expr:
        return False
    if toast_kind is None:
        return True
    return f'"{toast_kind}"' in function_expr


def _is_redirect_event(event: EventSpec, path: str | None = None) -> bool:
    """Check whether event is redirect, optionally by route path."""
    args_map = _event_args_map(event)
    if "path" not in args_map:
        return False
    if path is None:
        return True
    path_arg = args_map.get("path")
    return getattr(path_arg, "_var_value", None) == path


def _assert_toast_event(result: object, toast_kind: str | None = None) -> None:
    """Assert at least one toast event exists in handler output."""
    events = _as_event_list(result)
    assert events
    assert any(_is_toast_event(event, toast_kind=toast_kind) for event in events)


@pytest.mark.parametrize("state_cls", [AthleteState, RefereeState, TeamState])
def test_state_classes_remove_transient_success_message(state_cls: type) -> None:
    assert "success_message" not in state_cls.__dict__


def test_athlete_validate_form_still_sets_inline_validation_error() -> None:
    state = AthleteState()
    state.name = ""
    state.date_of_birth = "2000-05-01"
    state.gender = "FEMALE"

    assert state.validate_form() is False
    assert state.error_message == "Name must be 2-255 characters"


def test_referee_validate_form_still_sets_inline_validation_error() -> None:
    state = RefereeState()
    state.name = "A"
    state.license_number = "REF-001"

    assert state.validate_form() is False
    assert state.error_message == "Name must be 2-255 characters"


def test_team_validate_form_still_sets_inline_validation_error() -> None:
    state = TeamState()
    state.name = "Equipo válido"
    state.category_id = ""

    assert state.validate_form() is False
    assert state.error_message == "Category is required"


@pytest.mark.anyio
async def test_save_athlete_duplicate_name_uses_toast_feedback(sample_athlete) -> None:
    state = AthleteState()
    state.is_editing = False
    state.name = sample_athlete.name
    state.date_of_birth = "2000-05-01"
    state.gender = "FEMALE"
    state.weight_kg = "55"

    result = await AthleteState.save_athlete.fn(state)

    _assert_toast_event(result)
    assert state.error_message == ""


@pytest.mark.anyio
async def test_export_without_tournament_uses_toast_feedback() -> None:
    state = ExportState()

    result = await ExportState.export_tournament_results.fn(state)

    _assert_toast_event(result)


def test_viewer_access_denied_returns_toast_feedback() -> None:
    state = ViewerState()

    result = ViewerState.validate_tournament_access.fn(state, 999)

    _assert_toast_event(result)
    assert state.access_denied is True


def test_viewer_access_allowed_returns_success_toast_feedback() -> None:
    state = ViewerState()
    state.viewer_code = "VALID-CODE"
    state.current_tournament = {"id": 77, "name": "Copa Test"}

    result = ViewerState.validate_tournament_access.fn(state, 77)

    events = _as_event_list(result)
    assert events
    assert any(_is_toast_event(event, toast_kind="success") for event in events)
    assert state.access_denied is False


def test_viewer_access_denied_when_tournament_id_mismatch() -> None:
    state = ViewerState()
    state.viewer_code = "VALID-CODE"
    state.current_tournament = {"id": 77, "name": "Copa Test"}

    result = ViewerState.validate_tournament_access.fn(state, 88)

    _assert_toast_event(result)
    assert state.access_denied is True


@pytest.mark.anyio
async def test_auth_login_error_keeps_inline_error_and_returns_error_toast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = AuthState()
    state.username = "bad-user"
    state.password = "bad-pass"

    monkeypatch.setattr(
        "kakumi_app.states.auth_state.AuthService.login_user",
        lambda username, password: (None, None, "Invalid username or password"),
    )

    result = await AuthState.login.fn(state)

    events = _as_event_list(result)
    assert events
    assert any(_is_toast_event(event, toast_kind="error") for event in events)
    assert not any(_is_redirect_event(event) for event in events)
    assert state.login_error == "Invalid username or password"
    assert state.is_logging_in is False


@pytest.mark.anyio
async def test_auth_login_success_returns_success_toast_then_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = AuthState()
    state.username = "admin"
    state.password = "StrongPass123!"

    monkeypatch.setattr(
        "kakumi_app.states.auth_state.AuthService.login_user",
        lambda username, password: ("access-token", "refresh-token", ""),
    )

    def fake_load_user_from_token(self) -> None:
        self.is_authenticated = True
        self.user_role = "ADMIN"

    monkeypatch.setattr(AuthState, "_load_user_from_token", fake_load_user_from_token)

    result = await AuthState.login.fn(state)

    events = _as_event_list(result)
    assert events
    assert _is_toast_event(events[0], toast_kind="success")
    assert _is_redirect_event(events[1], path="/")
    assert state.access_token == "access-token"
    assert state.refresh_token == "refresh-token"
    assert state.username == ""
    assert state.password == ""
    assert state.login_error == ""
    assert state.is_logging_in is False


@pytest.mark.anyio
async def test_auth_login_success_sets_serializable_current_user_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = AuthState()
    state.username = "admin"
    state.password = "StrongPass123!"

    monkeypatch.setattr(
        "kakumi_app.states.auth_state.AuthService.login_user",
        lambda username, password: ("access-token", "refresh-token", ""),
    )

    fake_user = SimpleNamespace(
        id=99,
        username="admin",
        email="admin@test.dev",
        role="ADMIN",
        is_active=True,
    )
    monkeypatch.setattr(
        "kakumi_app.states.auth_state.AuthService.get_current_user_from_token",
        lambda token: fake_user,
    )

    await AuthState.login.fn(state)

    assert isinstance(state.current_user, dict)
    assert state.current_user == {
        "id": 99,
        "username": "admin",
        "email": "admin@test.dev",
        "role": "ADMIN",
        "is_active": True,
    }


@pytest.mark.anyio
async def test_auth_logout_returns_toast_and_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = AuthState()
    state.access_token = "token-123"
    state.refresh_token = "refresh-123"
    state.is_authenticated = True
    state.user_role = "ADMIN"
    state.login_error = "something"
    called_tokens: list[str] = []

    monkeypatch.setattr(
        "kakumi_app.states.auth_state.AuthService.logout_user",
        lambda token: called_tokens.append(token) or True,
    )

    result = await AuthState.logout.fn(state)

    events = _as_event_list(result)
    assert events
    assert _is_toast_event(events[0], toast_kind="info")
    assert _is_redirect_event(events[1], path="/login")
    assert called_tokens == ["token-123"]
    assert state.access_token == ""
    assert state.refresh_token == ""
    assert state.is_authenticated is False
    assert state.user_role == ""
    assert state.login_error == ""
    assert state.session_expired is False


@pytest.mark.anyio
async def test_auth_session_timeout_returns_warning_toast_and_redirect() -> None:
    state = AuthState()
    state.access_token = "token-123"
    state.refresh_token = "refresh-123"
    state.is_authenticated = True
    state.user_role = "OPERATOR"
    state.last_activity = "2000-01-01T00:00:00"

    result = await AuthState.check_session_timeout.fn(state)

    events = _as_event_list(result)
    assert events
    assert _is_toast_event(events[0], toast_kind="warning")
    assert _is_redirect_event(events[1], path="/login")
    assert state.access_token == ""
    assert state.refresh_token == ""
    assert state.is_authenticated is False
    assert state.user_role == ""
    assert state.session_expired is True


@pytest.mark.anyio
async def test_save_athlete_success_returns_toast_and_persists_row() -> None:
    state = AthleteState()
    state.name = "Atleta Éxito"
    state.date_of_birth = "2001-06-01"
    state.gender = "MALE"
    state.weight_kg = "68"
    state.show_form = True

    result = await AthleteState.save_athlete.fn(state)

    events = _as_event_list(result)
    assert events
    assert any(_is_toast_event(event, toast_kind="success") for event in events)
    assert state.show_form is False

    with rx.session() as session:
        athlete = session.exec(
            select(Athlete).where(Athlete.name == "Atleta Éxito")
        ).first()
    assert athlete is not None


@pytest.mark.anyio
async def test_delete_athlete_success_returns_toast_and_removes_row(
    sample_athlete,
) -> None:
    state = AthleteState()

    result = await AthleteState.delete_athlete.fn(state, sample_athlete.id)

    events = _as_event_list(result)
    assert events
    assert any(_is_toast_event(event, toast_kind="success") for event in events)

    with rx.session() as session:
        athlete = session.get(Athlete, sample_athlete.id)
    assert athlete is None


@pytest.mark.anyio
async def test_save_referee_success_returns_toast_and_persists_row() -> None:
    state = RefereeState()
    state.name = "Ref Éxito"
    state.license_number = "REF-SUCCESS-001"
    state.license_level = "NATIONAL"
    state.role = "REFEREE"
    state.show_form = True

    result = await RefereeState.save_referee.fn(state)

    events = _as_event_list(result)
    assert events
    assert any(_is_toast_event(event, toast_kind="success") for event in events)
    assert state.show_form is False

    with rx.session() as session:
        referee = session.exec(
            select(Referee).where(Referee.license_number == "REF-SUCCESS-001")
        ).first()
    assert referee is not None


@pytest.mark.anyio
async def test_save_team_success_returns_toast_and_persists_row(
    sample_category,
) -> None:
    state = TeamState()
    state.name = "Team Éxito"
    state.category_id = str(sample_category.id)
    state.dojo = "Dojo Test"
    state.show_form = True

    result = await TeamState.save_team.fn(state)

    events = _as_event_list(result)
    assert events
    assert any(_is_toast_event(event, toast_kind="success") for event in events)
    assert state.show_form is False

    with rx.session() as session:
        team = session.exec(select(Team).where(Team.name == "Team Éxito")).first()
    assert team is not None


@pytest.mark.anyio
async def test_export_with_selected_tournament_returns_success_toast_and_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = ExportState()
    state.selected_tournament_id = "12"
    state.export_format = "json"

    monkeypatch.setattr(
        "kakumi_app.states.export_state.ExportService.export_tournament_results_json",
        lambda tournament_id: f'{{"id": {tournament_id}}}',
    )

    result = await ExportState.export_tournament_results.fn(state)

    events = _as_event_list(result)
    assert events
    assert any(_is_toast_event(event, toast_kind="success") for event in events)
    assert state.export_content == '{"id": 12}'
    assert state.export_filename == "tournament_12_results.json"
    assert state.is_exporting is False


def test_export_load_tournaments_sets_serializable_dicts(sample_tournament) -> None:
    state = ExportState()

    ExportState.load_tournaments.fn(state)

    assert state.tournaments
    assert isinstance(state.tournaments[0], dict)
    assert state.tournaments[0]["id"] == sample_tournament.id


@pytest.mark.anyio
async def test_tournament_state_set_current_tournament_uses_dict_snapshot(
    sample_tournament,
) -> None:
    state = TournamentState()

    await TournamentState.set_current_tournament.fn(state, sample_tournament.id)

    assert isinstance(state.current_tournament, dict)
    assert state.current_tournament["id"] == sample_tournament.id


@pytest.mark.anyio
async def test_viewer_load_categories_queries_by_tournament_id(sample_category) -> None:
    state = ViewerState()
    state.current_tournament = {"id": sample_category.tournament_id}

    await ViewerState.load_categories.fn(state)

    assert state.categories
    assert isinstance(state.categories[0], dict)
    assert state.categories[0]["id"] == sample_category.id
    assert state.categories[0]["type"] == "kata"


def test_import_state_error_messages_persist_inline_until_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = ImportState()
    state.file_type = "csv"
    state.file_content = "name,date_of_birth,gender\n"
    persisted_errors = ["Row 2: name is required", "Row 3: invalid category"]

    def fake_import_csv(_: str) -> tuple[int, int, list[str]]:
        return (0, len(persisted_errors), persisted_errors)

    monkeypatch.setattr(
        "kakumi_app.states.import_state.ImportService.import_athletes_csv",
        fake_import_csv,
    )

    result = ImportState.import_athletes.fn(state)

    assert _as_event_list(result) == []
    assert state.success_count == 0
    assert state.error_count == 2
    assert state.error_messages == persisted_errors
    assert state.show_results is True

    ImportState.reset_import.fn(state)
    assert state.error_messages == []
    assert state.show_results is False


def test_pages_no_longer_reference_removed_feedback_state_vars() -> None:
    page_files = [
        ROOT / "kakumi_app/pages/admin/athletes_page.py",
        ROOT / "kakumi_app/pages/admin/referees_page.py",
        ROOT / "kakumi_app/pages/admin/teams_page.py",
    ]
    for file_path in page_files:
        content = file_path.read_text(encoding="utf-8")
        assert "success_message" not in content

    viewer_page = (ROOT / "kakumi_app/pages/viewer.py").read_text(encoding="utf-8")
    export_page = (ROOT / "kakumi_app/pages/admin/export_page.py").read_text(
        encoding="utf-8"
    )
    assert "state.error_message" not in viewer_page
    assert "state.error_message" not in export_page
