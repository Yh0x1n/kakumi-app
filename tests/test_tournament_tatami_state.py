"""Strict-TDD coverage for tournament-scoped tatami management."""

from __future__ import annotations

import datetime

import pytest
import reflex as rx
from sqlmodel import select

from kakumi_app.models.tournament_model import Match, MatchType, Tatami, Tournament


@pytest.mark.anyio
async def test_set_tournament_context_loads_only_selected_tatamis_and_repairs_mirror(
    sample_tournament,
    sample_user,
) -> None:
    from kakumi_app.states.tournament_tatami_state import TournamentTatamiState

    with rx.session() as session:
        selected_first = Tatami(
            name="Tatami A",
            location="Sector Norte",
            tournament_id=sample_tournament.id,
        )
        selected_second = Tatami(
            name="Tatami B",
            location="Sector Sur",
            tournament_id=sample_tournament.id,
            is_active=False,
        )
        other_tournament = Tournament(
            name="Torneo Secundario Tatami",
            venue="Dojo B",
            start_date=datetime.date(2026, 8, 1),
            end_date=datetime.date(2026, 8, 2),
            tatami_count=1,
            created_by_id=sample_user.id,
        )
        session.add(selected_first)
        session.add(selected_second)
        session.add(other_tournament)
        session.commit()
        session.refresh(other_tournament)

        drifted = session.get(Tournament, sample_tournament.id)
        assert drifted is not None
        drifted.tatami_count = 99
        session.add(drifted)
        session.add(Tatami(name="Tatami Externo", tournament_id=other_tournament.id))
        session.commit()

    state = TournamentTatamiState()

    await TournamentTatamiState.set_tournament_context.fn(state, sample_tournament.id)

    with rx.session() as session:
        repaired = session.get(Tournament, sample_tournament.id)

    assert state.current_tournament_id == sample_tournament.id
    assert state.current_tournament_name == sample_tournament.name
    assert [tatami["name"] for tatami in state.tatamis] == ["Tatami A", "Tatami B"]
    assert state.declared_tatami_count == 2
    assert state.active_tatami_count == 1
    assert repaired is not None
    assert repaired.tatami_count == 2


@pytest.mark.anyio
async def test_save_tatami_creates_row_and_updates_tournament_mirror(
    sample_tournament,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kakumi_app.states import tournament_tatami_state as state_module
    from kakumi_app.states.tournament_tatami_state import TournamentTatamiState

    monkeypatch.setattr(state_module.rx.toast, "success", lambda message: message)

    state = TournamentTatamiState()
    await TournamentTatamiState.set_tournament_context.fn(state, sample_tournament.id)
    state.name = "Tatami Central"
    state.location = "Cancha 1"

    result = await TournamentTatamiState.save_tatami.fn(state)

    with rx.session() as session:
        created = session.exec(
            select(Tatami).where(
                Tatami.tournament_id == sample_tournament.id,
                Tatami.name == "Tatami Central",
            )
        ).one()
        tournament = session.get(Tournament, sample_tournament.id)

    assert result == "Tatami 'Tatami Central' creado"
    assert created.location == "Cancha 1"
    assert created.is_active is True
    assert tournament is not None
    assert tournament.tatami_count == 1
    assert state.declared_tatami_count == 1
    assert state.active_tatami_count == 1


@pytest.mark.anyio
async def test_save_tatami_updates_existing_row_without_changing_count(
    sample_tournament,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kakumi_app.states import tournament_tatami_state as state_module
    from kakumi_app.states.tournament_tatami_state import TournamentTatamiState

    monkeypatch.setattr(state_module.rx.toast, "success", lambda message: message)

    with rx.session() as session:
        tatami = Tatami(
            name="Tatami Editar",
            location="Vieja",
            tournament_id=sample_tournament.id,
        )
        session.add(tatami)
        session.commit()
        session.refresh(tatami)

    state = TournamentTatamiState()
    await TournamentTatamiState.set_tournament_context.fn(state, sample_tournament.id)
    state.is_editing = True
    state.current_tatami = {"id": tatami.id}
    state.name = "Tatami Editado"
    state.location = "Nueva"

    result = await TournamentTatamiState.save_tatami.fn(state)

    with rx.session() as session:
        updated = session.get(Tatami, tatami.id)
        tournament = session.get(Tournament, sample_tournament.id)

    assert result == "Tatami 'Tatami Editado' actualizado"
    assert updated is not None
    assert updated.name == "Tatami Editado"
    assert updated.location == "Nueva"
    assert tournament is not None
    assert tournament.tatami_count == 1


@pytest.mark.anyio
async def test_toggle_tatami_active_updates_row_and_active_counter(
    sample_tournament,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kakumi_app.states import tournament_tatami_state as state_module
    from kakumi_app.states.tournament_tatami_state import TournamentTatamiState

    monkeypatch.setattr(state_module.rx.toast, "success", lambda message: message)

    with rx.session() as session:
        tatami = Tatami(
            name="Tatami Toggle",
            tournament_id=sample_tournament.id,
        )
        session.add(tatami)
        session.commit()
        session.refresh(tatami)

    state = TournamentTatamiState()
    await TournamentTatamiState.set_tournament_context.fn(state, sample_tournament.id)

    first = await TournamentTatamiState.toggle_tatami_active.fn(state, tatami.id)
    second = await TournamentTatamiState.toggle_tatami_active.fn(state, tatami.id)

    with rx.session() as session:
        refreshed = session.get(Tatami, tatami.id)

    assert first == "Tatami 'Tatami Toggle' desactivado"
    assert second == "Tatami 'Tatami Toggle' activado"
    assert refreshed is not None
    assert refreshed.is_active is True
    assert state.active_tatami_count == 1
    assert state.declared_tatami_count == 1


@pytest.mark.anyio
async def test_delete_tatami_blocks_when_current_match_exists(
    sample_tournament,
    sample_category,
) -> None:
    from kakumi_app.states.tournament_tatami_state import TournamentTatamiState

    with rx.session() as session:
        tatami = Tatami(
            name="Tatami Ocupado",
            tournament_id=sample_tournament.id,
        )
        session.add(tatami)
        session.commit()
        session.refresh(tatami)

        match = Match(
            tournament_id=sample_tournament.id,
            category_id=sample_category.id,
            round=1,
            position=1,
            match_number=1,
            match_type=MatchType.ELIMINATION.value,
        )
        session.add(match)
        session.commit()
        session.refresh(match)

        tatami.current_match_id = match.id
        session.add(tatami)
        session.commit()
        tatami_id = tatami.id

    state = TournamentTatamiState()
    await TournamentTatamiState.set_tournament_context.fn(state, sample_tournament.id)

    result = await TournamentTatamiState.delete_tatami.fn(state, tatami_id)

    with rx.session() as session:
        persisted = session.get(Tatami, tatami_id)

    assert result is None
    assert state.error_message == "No se puede eliminar tatami con encuentro actual asignado"
    assert persisted is not None


@pytest.mark.anyio
async def test_delete_tatami_removes_row_and_updates_tournament_mirror(
    sample_tournament,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kakumi_app.states import tournament_tatami_state as state_module
    from kakumi_app.states.tournament_tatami_state import TournamentTatamiState

    monkeypatch.setattr(state_module.rx.toast, "success", lambda message: message)

    with rx.session() as session:
        tatami = Tatami(
            name="Tatami Borrable",
            tournament_id=sample_tournament.id,
        )
        session.add(tatami)
        session.commit()
        session.refresh(tatami)
        tatami_id = tatami.id

    state = TournamentTatamiState()
    await TournamentTatamiState.set_tournament_context.fn(state, sample_tournament.id)

    result = await TournamentTatamiState.delete_tatami.fn(state, tatami_id)

    with rx.session() as session:
        deleted = session.get(Tatami, tatami_id)
        tournament = session.get(Tournament, sample_tournament.id)

    assert result == "Tatami 'Tatami Borrable' eliminado"
    assert deleted is None
    assert tournament is not None
    assert tournament.tatami_count == 0
    assert state.tatamis == []


@pytest.mark.anyio
async def test_delete_tatami_rejects_cross_tournament_delete(
    sample_tournament,
    sample_user,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kakumi_app.states import tournament_tatami_state as state_module
    from kakumi_app.states.tournament_tatami_state import TournamentTatamiState

    monkeypatch.setattr(state_module.rx.toast, "error", lambda message: message)

    with rx.session() as session:
        other_tournament = Tournament(
            name="Torneo Ajeno Tatamis",
            venue="Otra sede",
            start_date=datetime.date(2027, 7, 1),
            end_date=datetime.date(2027, 7, 2),
            tatami_count=1,
            created_by_id=sample_user.id,
        )
        session.add(other_tournament)
        session.commit()
        session.refresh(other_tournament)

        foreign_tatami = Tatami(
            name="Tatami Ajeno",
            tournament_id=other_tournament.id,
        )
        session.add(foreign_tatami)
        session.commit()
        session.refresh(foreign_tatami)

    state = TournamentTatamiState()
    await TournamentTatamiState.set_tournament_context.fn(state, sample_tournament.id)

    result = await TournamentTatamiState.delete_tatami.fn(state, foreign_tatami.id)

    with rx.session() as session:
        persisted = session.get(Tatami, foreign_tatami.id)

    assert result == "Tatami fuera del torneo seleccionado"
    assert state.error_message == "Tatami fuera del torneo seleccionado"
    assert persisted is not None
