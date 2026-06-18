"""Strict-TDD coverage for tournament-scoped manual category CRUD."""

from __future__ import annotations

import datetime

import pytest
import reflex as rx
from sqlmodel import select

from kakumi_app.models.tournament_model import (
    CompetitionSystem,
    Match,
    MatchType,
    Modality,
    Tournament,
    TournamentCategory,
)
from kakumi_app.states.tournament_category_state import TournamentCategoryState


@pytest.mark.anyio
async def test_set_tournament_context_loads_only_selected_tournament_categories(
    sample_tournament,
    sample_user,
) -> None:
    with rx.session() as session:
        selected_first = TournamentCategory(
            name="Kata Senior A",
            modality=Modality.KATA_INDIVIDUAL.value,
            gender="MALE",
            min_age=18,
            max_age=34,
            competition_system=CompetitionSystem.ELIMINATION.value,
            bracket_size=8,
            tournament_id=sample_tournament.id,
        )
        selected_second = TournamentCategory(
            name="Kata Senior B",
            modality=Modality.KATA_INDIVIDUAL.value,
            gender="FEMALE",
            min_age=18,
            max_age=35,
            competition_system=CompetitionSystem.ROUND_ROBIN.value,
            bracket_size=4,
            tournament_id=sample_tournament.id,
        )
        other_tournament = Tournament(
            name="Torneo Alterno",
            venue="Dojo Secundario",
            start_date=datetime.date(2026, 7, 1),
            end_date=datetime.date(2026, 7, 2),
            tatami_count=1,
            created_by_id=sample_user.id,
        )
        session.add(selected_first)
        session.add(selected_second)
        session.add(other_tournament)
        session.commit()
        session.refresh(other_tournament)

        session.add(
            TournamentCategory(
                name="No Debe Aparecer",
                modality=Modality.KUMITE_INDIVIDUAL.value,
                gender="MIXED",
                min_age=14,
                max_age=17,
                competition_system=CompetitionSystem.ELIMINATION.value,
                bracket_size=8,
                tournament_id=other_tournament.id,
            )
        )
        session.commit()

    state = TournamentCategoryState()

    await TournamentCategoryState.set_tournament_context.fn(state, sample_tournament.id)

    assert state.current_tournament_id == sample_tournament.id
    assert state.current_tournament_name == sample_tournament.name
    assert [category["name"] for category in state.categories] == [
        "Kata Senior A",
        "Kata Senior B",
    ]


@pytest.mark.anyio
async def test_save_category_creates_manual_category_with_age_and_belt_fields(
    sample_tournament,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kakumi_app.states import tournament_category_state as state_module

    monkeypatch.setattr(state_module.rx.toast, "success", lambda message: message)

    state = TournamentCategoryState()
    await TournamentCategoryState.set_tournament_context.fn(state, sample_tournament.id)
    state.name = "Kumite Cadete Danes"
    state.modality = "Kumite Individual"
    state.gender = "Femenino"
    state.min_age = "14"
    state.max_age = "15"
    state.min_belt_rank = "Negro"
    state.max_belt_rank = "Negro"
    state.competition_system = "Liguilla"
    state.bracket_size = "4"

    result = await TournamentCategoryState.save_category.fn(state)

    with rx.session() as session:
        created = session.exec(
            select(TournamentCategory).where(
                TournamentCategory.tournament_id == sample_tournament.id,
                TournamentCategory.name == "Kumite Cadete Danes",
            )
        ).one()

    assert result == "Categoría 'Kumite Cadete Danes' creada"
    assert created.modality == Modality.KUMITE_INDIVIDUAL.value
    assert created.gender == "FEMALE"
    assert created.min_age == 14
    assert created.max_age == 15
    assert created.min_belt_rank == "Negro"
    assert created.max_belt_rank == "Negro"
    assert created.competition_system == CompetitionSystem.ROUND_ROBIN.value
    assert created.bracket_size == 4
    assert any(
        category["name"] == "Kumite Cadete Danes" for category in state.categories
    )


@pytest.mark.anyio
async def test_save_category_rejects_invalid_age_range_before_db_write(
    sample_tournament,
) -> None:
    state = TournamentCategoryState()
    await TournamentCategoryState.set_tournament_context.fn(state, sample_tournament.id)
    state.name = "Edad Invertida"
    state.min_age = "18"
    state.max_age = "17"

    result = await TournamentCategoryState.save_category.fn(state)

    with rx.session() as session:
        created = session.exec(
            select(TournamentCategory).where(
                TournamentCategory.tournament_id == sample_tournament.id,
                TournamentCategory.name == "Edad Invertida",
            )
        ).first()

    assert result is None
    assert state.error_message == "Edad mínima no puede ser mayor que edad máxima"
    assert created is None


@pytest.mark.anyio
async def test_save_category_rejects_invalid_belt_rank_before_db_write(
    sample_tournament,
) -> None:
    state = TournamentCategoryState()
    await TournamentCategoryState.set_tournament_context.fn(state, sample_tournament.id)
    state.name = "Cinturón Inválido"
    state.min_belt_rank = "Purple"
    state.max_belt_rank = "Dan 2"

    result = await TournamentCategoryState.save_category.fn(state)

    with rx.session() as session:
        created = session.exec(
            select(TournamentCategory).where(
                TournamentCategory.tournament_id == sample_tournament.id,
                TournamentCategory.name == "Cinturón Inválido",
            )
        ).first()

    assert result is None
    assert state.error_message == "Grado mínimo inválido"
    assert created is None


@pytest.mark.anyio
async def test_save_category_updates_existing_manual_category(
    sample_tournament,
    sample_category,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kakumi_app.states import tournament_category_state as state_module

    monkeypatch.setattr(state_module.rx.toast, "success", lambda message: message)

    state = TournamentCategoryState()
    await TournamentCategoryState.set_tournament_context.fn(state, sample_tournament.id)
    state.is_editing = True
    state.current_category = {"id": sample_category.id}
    state.name = "Kata Senior Editada"
    state.modality = "Kata Individual"
    state.gender = "Masculino"
    state.min_age = "21"
    state.max_age = "39"
    state.min_belt_rank = "Blanco"
    state.max_belt_rank = "Negro"
    state.competition_system = "Liguilla"
    state.bracket_size = "4"

    result = await TournamentCategoryState.save_category.fn(state)

    with rx.session() as session:
        updated = session.get(TournamentCategory, sample_category.id)

    assert result == "Categoría 'Kata Senior Editada' actualizada"
    assert updated is not None
    assert updated.name == "Kata Senior Editada"
    assert updated.min_age == 21
    assert updated.max_age == 39
    assert updated.min_belt_rank == "Blanco"
    assert updated.max_belt_rank == "Negro"
    assert updated.competition_system == CompetitionSystem.ROUND_ROBIN.value
    assert updated.bracket_size == 4


@pytest.mark.anyio
async def test_delete_category_blocks_when_related_matches_exist(
    sample_tournament,
    sample_category,
) -> None:
    with rx.session() as session:
        session.add(
            Match(
                tournament_id=sample_tournament.id,
                category_id=sample_category.id,
                round=1,
                position=1,
                match_number=1,
                match_type=MatchType.ELIMINATION.value,
            )
        )
        session.commit()

    state = TournamentCategoryState()
    await TournamentCategoryState.set_tournament_context.fn(state, sample_tournament.id)

    result = await TournamentCategoryState.delete_category.fn(state, sample_category.id)

    with rx.session() as session:
        persisted = session.get(TournamentCategory, sample_category.id)

    assert result is None
    assert (
        state.error_message
        == "No se puede eliminar categoría con encuentros relacionados"
    )
    assert persisted is not None


@pytest.mark.anyio
async def test_delete_category_removes_manual_category_without_matches(
    sample_tournament,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kakumi_app.states import tournament_category_state as state_module

    monkeypatch.setattr(state_module.rx.toast, "success", lambda message: message)

    with rx.session() as session:
        category = TournamentCategory(
            name="Kumite Borrable",
            modality=Modality.KUMITE_INDIVIDUAL.value,
            gender="MALE",
            min_age=18,
            max_age=35,
            competition_system=CompetitionSystem.ELIMINATION.value,
            bracket_size=8,
            tournament_id=sample_tournament.id,
        )
        session.add(category)
        session.commit()
        session.refresh(category)
        category_id = category.id

    state = TournamentCategoryState()
    await TournamentCategoryState.set_tournament_context.fn(state, sample_tournament.id)

    result = await TournamentCategoryState.delete_category.fn(state, category_id)

    with rx.session() as session:
        deleted = session.get(TournamentCategory, category_id)

    assert result == "Categoría 'Kumite Borrable' eliminada"
    assert deleted is None
    assert all(category["id"] != category_id for category in state.categories)


@pytest.mark.anyio
async def test_delete_category_rejects_cross_tournament_delete(
    sample_tournament,
    sample_user,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kakumi_app.states import tournament_category_state as state_module

    monkeypatch.setattr(state_module.rx.toast, "error", lambda message: message)

    with rx.session() as session:
        other_tournament = Tournament(
            name="Torneo Ajeno Categorías",
            venue="Otra sede",
            start_date=datetime.date(2027, 6, 1),
            end_date=datetime.date(2027, 6, 2),
            tatami_count=1,
            created_by_id=sample_user.id,
        )
        session.add(other_tournament)
        session.commit()
        session.refresh(other_tournament)

        foreign_category = TournamentCategory(
            name="Categoría Ajena",
            modality=Modality.KATA_INDIVIDUAL.value,
            gender="MALE",
            min_age=18,
            max_age=35,
            competition_system=CompetitionSystem.ELIMINATION.value,
            bracket_size=8,
            tournament_id=other_tournament.id,
        )
        session.add(foreign_category)
        session.commit()
        session.refresh(foreign_category)

    state = TournamentCategoryState()
    await TournamentCategoryState.set_tournament_context.fn(state, sample_tournament.id)

    result = await TournamentCategoryState.delete_category.fn(
        state,
        foreign_category.id,
    )

    with rx.session() as session:
        persisted = session.get(TournamentCategory, foreign_category.id)

    assert result == "Categoría fuera del torneo seleccionado"
    assert state.error_message == "Categoría fuera del torneo seleccionado"
    assert persisted is not None


@pytest.mark.anyio
async def test_validate_form_kata_fields_valid(
    sample_tournament,
) -> None:
    """_validate_form() succeeds with valid kata-specific fields."""
    state = TournamentCategoryState()
    await TournamentCategoryState.set_tournament_context.fn(state, sample_tournament.id)
    state.name = "Kata Valid Test"
    state.modality = "Kata Individual"
    state.gender = "Masculino"
    state.min_age = "18"
    state.max_age = "35"
    state.competition_system = "Eliminación Directa"
    state.bracket_size = "8"
    state.form_judge_panel_size = "5"
    state.form_kata_flow_mode = "STANDARD"
    state.form_scoring_type = "average-with-discard"

    payload = state._validate_form()

    assert payload is not None
    assert payload["name"] == "Kata Valid Test"
    assert payload["judge_panel_size"] == 5
    assert payload["kata_flow_mode"] == "STANDARD"
    assert payload["scoring_type"] == "average-with-discard"


@pytest.mark.anyio
async def test_validate_form_rejects_invalid_judge_panel_size(
    sample_tournament,
) -> None:
    """_validate_form() rejects judge_panel_size not in {3,5,7}."""
    state = TournamentCategoryState()
    await TournamentCategoryState.set_tournament_context.fn(state, sample_tournament.id)
    state.name = "Kata Invalid Panel"
    state.modality = "Kata Individual"
    state.gender = "Masculino"
    state.min_age = "18"
    state.max_age = "35"
    state.competition_system = "Eliminación Directa"
    state.bracket_size = "8"
    state.form_judge_panel_size = "2"

    payload = state._validate_form()

    assert payload is None
    assert state.error_message == "Panel de jueces debe ser 3, 5 o 7"


@pytest.mark.anyio
async def test_validate_form_rejects_invalid_scoring_type(
    sample_tournament,
) -> None:
    """_validate_form() rejects invalid scoring_type for STANDARD flow."""
    state = TournamentCategoryState()
    await TournamentCategoryState.set_tournament_context.fn(state, sample_tournament.id)
    state.name = "Kata Invalid Score"
    state.modality = "Kata Individual"
    state.gender = "Masculino"
    state.min_age = "18"
    state.max_age = "35"
    state.competition_system = "Eliminación Directa"
    state.bracket_size = "8"
    state.form_judge_panel_size = "3"
    state.form_kata_flow_mode = "STANDARD"
    state.form_scoring_type = "INVALID"

    payload = state._validate_form()

    assert payload is None
    assert state.error_message == "Tipo de puntuación inválido"


@pytest.mark.anyio
async def test_validate_form_informal_flow_uses_informal_scoring(
    sample_tournament,
) -> None:
    """INFORMAL kata_flow_mode forces scoring_type to INFORMAL."""
    state = TournamentCategoryState()
    await TournamentCategoryState.set_tournament_context.fn(state, sample_tournament.id)
    state.name = "Kata Informal"
    state.modality = "Kata Individual"
    state.gender = "Masculino"
    state.min_age = "18"
    state.max_age = "35"
    state.competition_system = "Eliminación Directa"
    state.bracket_size = "8"
    state.form_judge_panel_size = "3"
    state.form_kata_flow_mode = "INFORMAL"
    state.form_scoring_type = "INFORMAL"

    payload = state._validate_form()

    assert payload is not None
    assert payload["kata_flow_mode"] == "INFORMAL"
    assert payload["scoring_type"] == "INFORMAL"


@pytest.mark.anyio
async def test_serialize_category_includes_kata_fields(
    sample_tournament,
) -> None:
    """_serialize_category() includes judge_panel_size, kata_flow_mode, scoring_type."""
    with rx.session() as session:
        category = TournamentCategory(
            name="Kata Serialize Test",
            modality=Modality.KATA_INDIVIDUAL.value,
            gender="MALE",
            min_age=18,
            max_age=35,
            competition_system=CompetitionSystem.ELIMINATION.value,
            bracket_size=8,
            tournament_id=sample_tournament.id,
            judge_panel_size=5,
            kata_flow_mode="INFORMAL",
            scoring_type="INFORMAL",
        )
        session.add(category)
        session.commit()
        session.refresh(category)

    state = TournamentCategoryState()
    result = state._serialize_category(category)

    assert result["judge_panel_size"] == 5
    assert result["kata_flow_mode"] == "INFORMAL"
    assert result["scoring_type"] == "INFORMAL"
    assert result["name"] == "Kata Serialize Test"
