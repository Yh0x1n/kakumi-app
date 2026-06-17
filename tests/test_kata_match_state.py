"""Tests for KataMatchState exhibition/tournament live flow."""

from __future__ import annotations

from typing import Any

import pytest
import reflex as rx
from reflex.istate.data import PageData
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.kata_model import KataJudgeScore
from kakumi_app.models.tournament_model import (
    CategoryGender,
    CategoryStatus,
    CompetitionSystem,
    Match,
    MatchStatus,
    Modality,
    TournamentCategory,
)
from kakumi_app.services.kata_scoring_service import KataScoringService
from kakumi_app.states.kata_match_state import KataMatchState


def _event_fn(event_callback: Any) -> Any:
    return event_callback.fn


def _set_match_route_param(state: KataMatchState, match_id: int | str) -> None:
    object.__setattr__(
        state.router,
        "_page",
        PageData(params={"match_id": str(match_id)}),
    )


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_enable_exhibition_mode_publishes_exhibition_secondary_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KataMatchState()

    calls: dict[str, object] = {}

    class _FakeDisplaySession:
        display_key = "kata-exh-key"

    def _ensure(**kwargs):
        calls["ensure"] = kwargs
        return _FakeDisplaySession()

    def _publish(*, display_key: str, snapshot: dict[str, object]):
        calls["publish"] = {
            "display_key": display_key,
            "snapshot": snapshot,
        }
        return _FakeDisplaySession()

    monkeypatch.setattr(
        "kakumi_app.states.kata_match_state.SecondaryDisplayService.ensure_display_session",
        _ensure,
    )
    monkeypatch.setattr(
        "kakumi_app.states.kata_match_state.SecondaryDisplayService.publish_snapshot",
        _publish,
    )

    await _event_fn(KataMatchState.enable_exhibition_mode)(state)

    assert calls["ensure"] == {
        "modality": "KATA",
        "source_kind": "EXHIBITION",
        "match_id": None,
    }
    assert state.public_display_key == "kata-exh-key"
    snapshot = calls["publish"]["snapshot"]  # type: ignore[index]
    assert snapshot["source_kind"] == "EXHIBITION"
    assert snapshot["match_id"] is None


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_enable_exhibition_mode_starts_free_operation_defaults() -> None:
    state = KataMatchState()

    await _event_fn(KataMatchState.enable_exhibition_mode)(state)

    assert state.is_exhibition_mode is True
    assert state.has_active_match is False
    assert state.match_id == 0
    assert state.judge_panel_size == 5
    assert state.panel_complete is False


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_load_match_tournament_sets_kata_contract_fields(
    kata_match,
) -> None:
    state = KataMatchState()
    _set_match_route_param(state, kata_match.id)

    await _event_fn(KataMatchState.load_match)(state)

    assert state.match_id == kata_match.id
    assert state.is_exhibition_mode is False
    assert state.has_active_match is True
    assert state.scoring_type in {"STANDARD", "FLAG"}
    assert state.decision_rule in {
        "average-with-discard",
        "majority-by-judge",
    }
    assert state.judge_panel_size in {3, 5}


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_finalize_exhibition_requires_complete_panel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KataMatchState()
    await _event_fn(KataMatchState.enable_exhibition_mode)(state)

    def toast_error(message: str) -> str:
        return f"toast:{message}"

    monkeypatch.setattr(
        "kakumi_app.states.kata_match_state.rx.toast.error",
        toast_error,
    )

    events = [event async for event in state.finalize_match()]

    assert events == ["toast:Panel incompleto"]
    assert state.error_message == "Panel incompleto"
    assert state.winner_participant == ""


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_finalize_exhibition_majority_sets_winner_without_db_writes(
    sample_judges,
) -> None:
    state = KataMatchState()
    await _event_fn(KataMatchState.enable_exhibition_mode)(state)
    state.judge_panel_size = 3
    state.decision_rule = "majority-by-judge"
    state._set_numerical_entry("J1", "AKA", "8.0")
    state._set_numerical_entry("J1", "AO", "7.0")
    state._set_numerical_entry("J2", "AKA", "8.1")
    state._set_numerical_entry("J2", "AO", "7.1")
    state._set_numerical_entry("J3", "AKA", "7.0")
    state._set_numerical_entry("J3", "AO", "8.0")

    before_scores = 0
    with rx.session() as session:
        before_scores = len(session.exec(select(KataJudgeScore)).all())

    events = [event async for event in state.finalize_match()]

    with rx.session() as session:
        after_scores = len(session.exec(select(KataJudgeScore)).all())

    assert events == []
    assert state.error_message == ""
    assert state.winner_participant == "AKA"
    assert after_scores == before_scores


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_exhibition_can_switch_decision_rule_from_scoreboard_state() -> None:
    state = KataMatchState()
    await _event_fn(KataMatchState.enable_exhibition_mode)(state)
    await _event_fn(KataMatchState.set_panel_size)(state, 3)
    await _event_fn(KataMatchState.set_judge_score)(state, "J1", "AKA", "9.0")
    await _event_fn(KataMatchState.set_judge_score)(state, "J1", "AO", "8.0")
    await _event_fn(KataMatchState.set_judge_score)(state, "J2", "AKA", "9.0")
    await _event_fn(KataMatchState.set_judge_score)(state, "J2", "AO", "8.0")
    await _event_fn(KataMatchState.set_judge_score)(state, "J3", "AKA", "7.0")
    await _event_fn(KataMatchState.set_judge_score)(state, "J3", "AO", "9.9")

    default_events = [event async for event in state.finalize_match()]

    assert default_events == []
    assert state.winner_participant == "AO"

    _event_fn(KataMatchState.set_decision_rule)(state, "majority-by-judge")
    switched_events = [event async for event in state.finalize_match()]

    assert switched_events == []
    assert state.winner_participant == "AKA"


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_tournament_cannot_override_category_decision_rule_from_scoreboard(
    kata_match,
) -> None:
    state = KataMatchState()
    _set_match_route_param(state, kata_match.id)
    await _event_fn(KataMatchState.load_match)(state)
    category_rule = state.decision_rule

    _event_fn(KataMatchState.set_decision_rule)(state, "majority-by-judge")

    assert state.decision_rule == category_rule


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_finalize_tournament_rejects_incomplete_panel(
    kata_match,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KataMatchState()
    _set_match_route_param(state, kata_match.id)
    await _event_fn(KataMatchState.load_match)(state)

    def toast_error(message: str) -> str:
        return f"toast:{message}"

    monkeypatch.setattr(
        "kakumi_app.states.kata_match_state.rx.toast.error",
        toast_error,
    )

    events = [event async for event in state.finalize_match()]

    assert events == ["toast:Panel incompleto"]
    assert state.error_message == "Panel incompleto"


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_finalize_tournament_persists_scores_and_winner(
    kata_match,
    sample_judges,
) -> None:
    sample_judges(5)
    state = KataMatchState()
    _set_match_route_param(state, kata_match.id)
    await _event_fn(KataMatchState.load_match)(state)
    state.judge_panel_size = 5
    state.decision_rule = "average-with-discard"
    for index in range(1, 6):
        slot = f"J{index}"
        state._set_numerical_entry(slot, "AKA", f"{8.5 + (0.1 * index):.1f}")
        state._set_numerical_entry(slot, "AO", f"{7.4 + (0.1 * index):.1f}")

    events = [event async for event in state.finalize_match()]

    with rx.session() as session:
        match = session.get(Match, kata_match.id)
        scores = session.exec(
            select(KataJudgeScore).where(KataJudgeScore.match_id == kata_match.id)
        ).all()

    assert events == []
    assert state.error_message == ""
    assert state.winner_participant == "AKA"
    assert match is not None
    assert match.status == MatchStatus.COMPLETED.value
    assert len(scores) == 10


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_finalize_tournament_flag_mode_persists_three_votes(
    kata_match,
    sample_judges,
) -> None:
    sample_judges(3)
    with rx.session() as session:
        match = session.get(Match, kata_match.id)
        assert match is not None
        category = match.category
        category.judge_panel_size = 3
        category.scoring_type = "FLAG"
        session.add(category)
        session.commit()

    state = KataMatchState()
    _set_match_route_param(state, kata_match.id)
    await _event_fn(KataMatchState.load_match)(state)
    await _event_fn(KataMatchState.set_flag_vote)(state, "J1", "AKA")
    await _event_fn(KataMatchState.set_flag_vote)(state, "J2", "AKA")
    await _event_fn(KataMatchState.set_flag_vote)(state, "J3", "AO")

    events = [event async for event in state.finalize_match()]

    with rx.session() as session:
        scores = session.exec(
            select(KataJudgeScore).where(KataJudgeScore.match_id == kata_match.id)
        ).all()

    assert events == []
    assert state.winner_participant == "AKA"
    assert len(scores) == 3
    assert all(score.is_flag_mode for score in scores)


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_finalize_tournament_updates_standings_and_bunkai_contract(
    kata_match,
    sample_judges,
) -> None:
    sample_judges(5)
    with rx.session() as session:
        match = session.get(Match, kata_match.id)
        assert match is not None
        category = match.category
        category.bunkai_mode = "ALL_ROUNDS"
        session.add(category)
        session.commit()

    state = KataMatchState()
    _set_match_route_param(state, kata_match.id)
    await _event_fn(KataMatchState.load_match)(state)
    state.judge_panel_size = 5
    state.decision_rule = "average-with-discard"

    for index in range(1, 6):
        slot = f"J{index}"
        state._set_numerical_entry(slot, "AKA", f"{8.5 + (0.1 * index):.1f}")
        state._set_numerical_entry(slot, "AO", f"{7.2 + (0.1 * index):.1f}")

    events = [event async for event in state.finalize_match()]

    with rx.session() as session:
        match = session.get(Match, kata_match.id)
        scores = session.exec(
            select(KataJudgeScore).where(KataJudgeScore.match_id == kata_match.id)
        ).all()

    assert events == []
    assert state.error_message == ""
    assert match is not None
    assert match.status == MatchStatus.COMPLETED.value
    assert match.bunkai_required is True
    assert len(scores) == 10

    standings = KataScoringService.calculate_standings(match.category_id)

    assert standings
    assert standings[0].athlete_id == match.aka_id
    assert standings[0].victory_points == 3


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_enable_exhibition_mode_initializes_informal_single_panel_state() -> None:
    state = KataMatchState()

    await _event_fn(KataMatchState.enable_exhibition_mode)(state)

    assert state.kata_mode == "STANDARD"
    assert state.informal_selected_athlete_label == ""
    assert state.informal_current_athlete_label == ""
    assert state.informal_roster_labels == []
    assert state.informal_standings == []
    assert state.informal_judge_entries == {
        "J1": "",
        "J2": "",
        "J3": "",
        "J4": "",
        "J5": "",
    }


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_finalize_exhibition_informal_saves_and_advances_participant() -> None:
    state = KataMatchState()
    await _event_fn(KataMatchState.enable_exhibition_mode)(state)
    await _event_fn(KataMatchState.set_kata_mode)(state, "INFORMAL")
    await _event_fn(KataMatchState.set_informal_exhibition_participant_name)(
        state, "Lucía"
    )

    for slot in ("J1", "J2", "J3", "J4", "J5"):
        await _event_fn(KataMatchState.set_informal_judge_score)(state, slot, "8.2")

    events = [event async for event in state.finalize_match()]

    assert events == []
    assert state.error_message == ""
    assert state.informal_exhibition_participant_name == ""
    assert state.informal_current_athlete_label == "ATLETA"
    assert state.informal_judge_entries == {
        "J1": "",
        "J2": "",
        "J3": "",
        "J4": "",
        "J5": "",
    }
    assert len(state.informal_standings) == 1
    assert state.informal_standings[0]["athlete_name"] == "Lucía"


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_exhibition_informal_works_without_category_and_uses_fallback_name() -> (
    None
):
    state = KataMatchState()
    await _event_fn(KataMatchState.enable_exhibition_mode)(state)

    await _event_fn(KataMatchState.set_kata_mode)(state, "INFORMAL")

    assert state.kata_mode == "INFORMAL"
    assert state.error_message == ""
    assert state.informal_category_id == 0
    assert state.informal_current_athlete_label == "ATLETA"

    for slot in ("J1", "J2", "J3", "J4", "J5"):
        await _event_fn(KataMatchState.set_informal_judge_score)(state, slot, "8.0")

    events = [event async for event in state.finalize_match()]

    assert events == []
    assert len(state.informal_standings) == 1
    assert state.informal_standings[0]["athlete_name"] == "ATLETA"


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_tournament_load_match_activates_informal_single_panel_for_category(
    kata_match,
) -> None:
    with rx.session() as session:
        match = session.get(Match, kata_match.id)
        assert match is not None
        category = match.category
        category.kata_flow_mode = "INFORMAL"
        session.add(category)
        session.commit()

    state = KataMatchState()
    _set_match_route_param(state, kata_match.id)

    await _event_fn(KataMatchState.load_match)(state)

    assert state.kata_mode == "INFORMAL"


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_load_match_publishes_secondary_display_snapshot(
    kata_match,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KataMatchState()
    _set_match_route_param(state, kata_match.id)

    calls: dict[str, object] = {}

    class _FakeDisplaySession:
        display_key = "kata-key"

    def _ensure(**kwargs):
        calls["ensure"] = kwargs
        return _FakeDisplaySession()

    def _publish(*, display_key: str, snapshot: dict[str, object]):
        calls["publish"] = {
            "display_key": display_key,
            "snapshot": snapshot,
        }
        return _FakeDisplaySession()

    monkeypatch.setattr(
        "kakumi_app.states.kata_match_state.SecondaryDisplayService.ensure_display_session",
        _ensure,
    )
    monkeypatch.setattr(
        "kakumi_app.states.kata_match_state.SecondaryDisplayService.publish_snapshot",
        _publish,
    )

    await _event_fn(KataMatchState.load_match)(state)

    assert state.public_display_key == "kata-key"
    assert calls["ensure"] == {
        "modality": "KATA",
        "source_kind": "TOURNAMENT",
        "match_id": kata_match.id,
    }
    snapshot = calls["publish"]["snapshot"]  # type: ignore[index]
    assert snapshot["modality"] == "KATA"
    assert snapshot["source_kind"] == "TOURNAMENT"


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_reset_entries_repulishes_secondary_display_snapshot_in_exhibition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KataMatchState()
    await _event_fn(KataMatchState.enable_exhibition_mode)(state)

    calls: list[dict[str, Any]] = []

    monkeypatch.setattr(
        "kakumi_app.states.kata_match_state.SecondaryDisplayService.publish_snapshot",
        lambda *, display_key, snapshot: calls.append(
            {"display_key": display_key, "snapshot": snapshot}
        ),
    )

    await _event_fn(KataMatchState.reset_entries)(state)

    assert calls
    assert state.public_display_key != ""
    assert calls[-1]["display_key"] == state.public_display_key
    snapshot = calls[-1]["snapshot"]
    assert isinstance(snapshot, dict)
    assert snapshot["source_kind"] == "EXHIBITION"


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_standard_snapshot_uses_sum_total_without_changing_decision_logic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KataMatchState()
    await _event_fn(KataMatchState.enable_exhibition_mode)(state)
    await _event_fn(KataMatchState.set_panel_size)(state, 3)
    state.kata_mode = "STANDARD"
    state.decision_rule = "average-with-discard"

    await _event_fn(KataMatchState.set_judge_score)(state, "J1", "AKA", "9.0")
    await _event_fn(KataMatchState.set_judge_score)(state, "J1", "AO", "8.0")
    await _event_fn(KataMatchState.set_judge_score)(state, "J2", "AKA", "9.0")
    await _event_fn(KataMatchState.set_judge_score)(state, "J2", "AO", "8.0")
    await _event_fn(KataMatchState.set_judge_score)(state, "J3", "AKA", "7.0")
    await _event_fn(KataMatchState.set_judge_score)(state, "J3", "AO", "9.9")

    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "kakumi_app.states.kata_match_state.SecondaryDisplayService.publish_snapshot",
        lambda *, display_key, snapshot: calls.append(snapshot),
    )

    await _event_fn(KataMatchState.set_judge_score)(state, "J3", "AO", "9.9")
    events = [event async for event in state.finalize_match()]

    assert events == []
    assert state.winner_participant == "AO"
    assert calls
    snapshot = calls[-1]
    assert snapshot["aka"]["total"] == "25.000"
    assert snapshot["ao"]["total"] == "25.900"


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_standard_snapshot_shows_judge_detail_only_after_votes_entered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KataMatchState()
    await _event_fn(KataMatchState.enable_exhibition_mode)(state)
    state.kata_mode = "STANDARD"

    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "kakumi_app.states.kata_match_state.SecondaryDisplayService.publish_snapshot",
        lambda *, display_key, snapshot: calls.append(snapshot),
    )

    await _event_fn(KataMatchState.reset_entries)(state)
    await _event_fn(KataMatchState.set_judge_score)(state, "J1", "AKA", "8.4")

    assert len(calls) >= 2
    before_votes = calls[-2]
    after_votes = calls[-1]
    assert before_votes["judge_detail_visible"] is False
    assert before_votes["judge_detail_lines"] == []
    assert after_votes["judge_detail_visible"] is True
    assert "J1: AKA 8.4 / AO —" in after_votes["judge_detail_lines"]


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_informal_snapshot_shows_judge_detail_only_after_votes_entered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KataMatchState()
    await _event_fn(KataMatchState.enable_exhibition_mode)(state)
    await _event_fn(KataMatchState.set_kata_mode)(state, "INFORMAL")

    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "kakumi_app.states.kata_match_state.SecondaryDisplayService.publish_snapshot",
        lambda *, display_key, snapshot: calls.append(snapshot),
    )

    await _event_fn(KataMatchState.reset_entries)(state)
    await _event_fn(KataMatchState.set_informal_judge_score)(state, "J2", "8.7")

    assert len(calls) >= 2
    before_votes = calls[-2]
    after_votes = calls[-1]
    assert before_votes["judge_detail_visible"] is False
    assert before_votes["judge_detail_lines"] == []
    assert after_votes["judge_detail_visible"] is True
    assert "J2: 8.7" in after_votes["judge_detail_lines"]


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_informal_snapshot_exposes_single_athlete_and_results_payload() -> None:
    state = KataMatchState()
    await _event_fn(KataMatchState.enable_exhibition_mode)(state)
    await _event_fn(KataMatchState.set_kata_mode)(state, "INFORMAL")
    await _event_fn(KataMatchState.set_informal_exhibition_participant_name)(
        state, "Lucía"
    )

    for slot in ("J1", "J2", "J3", "J4", "J5"):
        await _event_fn(KataMatchState.set_informal_judge_score)(state, slot, "8.2")

    _ = [event async for event in state.finalize_match()]
    snapshot = state._build_display_snapshot()

    assert snapshot["kata_mode"] == "INFORMAL"
    assert snapshot["informal"]["athlete_name"] == "ATLETA"
    assert len(snapshot["informal"]["results"]) == 1
    assert "Lucía" in snapshot["informal"]["results"][0]


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_standard_majority_snapshot_exposes_vote_tally() -> None:
    state = KataMatchState()
    await _event_fn(KataMatchState.enable_exhibition_mode)(state)
    await _event_fn(KataMatchState.set_panel_size)(state, 5)
    state.kata_mode = "STANDARD"
    state.decision_rule = "majority-by-judge"

    await _event_fn(KataMatchState.set_judge_score)(state, "J1", "AKA", "8.0")
    await _event_fn(KataMatchState.set_judge_score)(state, "J1", "AO", "7.0")
    await _event_fn(KataMatchState.set_judge_score)(state, "J2", "AKA", "8.1")
    await _event_fn(KataMatchState.set_judge_score)(state, "J2", "AO", "7.1")
    await _event_fn(KataMatchState.set_judge_score)(state, "J3", "AKA", "8.2")
    await _event_fn(KataMatchState.set_judge_score)(state, "J3", "AO", "7.2")
    await _event_fn(KataMatchState.set_judge_score)(state, "J4", "AKA", "7.0")
    await _event_fn(KataMatchState.set_judge_score)(state, "J4", "AO", "8.0")
    await _event_fn(KataMatchState.set_judge_score)(state, "J5", "AKA", "7.1")
    await _event_fn(KataMatchState.set_judge_score)(state, "J5", "AO", "8.1")

    snapshot = state._build_display_snapshot()

    assert snapshot["majority_tally_visible"] is True
    assert snapshot["majority_tally"] == "AKA 3 - AO 2"
    assert snapshot["majority_aka_votes"] == 3
    assert snapshot["majority_ao_votes"] == 2


def test_publish_display_snapshot_skipped_when_viewer_disconnected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KataMatchState()
    state.public_display_key = "kata-key"
    object.__setattr__(
        state.router,
        "session",
        type("Session", (), {"client_token": "disconnected-token"})(),
    )

    fake_app = type(
        "App",
        (),
        {
            "_token_manager": type(
                "TokenManager",
                (),
                {"token_to_socket": {}},
            )()
        },
    )()
    monkeypatch.setattr(rx.State, "_get_app", lambda: fake_app, raising=False)

    ensure_calls: list[dict[str, Any]] = []
    publish_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "kakumi_app.states.kata_match_state.SecondaryDisplayService.ensure_display_session",
        lambda **kwargs: ensure_calls.append(kwargs),
    )
    monkeypatch.setattr(
        "kakumi_app.states.kata_match_state.SecondaryDisplayService.publish_snapshot",
        lambda **kwargs: publish_calls.append(kwargs),
    )

    state._publish_display_snapshot()

    assert ensure_calls == []
    assert publish_calls == []
    assert state.public_display_key == "kata-key"
    assert state.display_status == ""


# ── Helpers for informal category tests ──


def _create_informal_cat(
    tournament_id: int, *, judge_panel_size: int = 5
) -> TournamentCategory:
    """Helper: create an informal tournament category in the DB."""
    with rx.session() as session:
        cat = TournamentCategory(
            name="Kata Informal TDD",
            modality=Modality.KATA_INDIVIDUAL.value,
            gender=CategoryGender.MIXED.value,
            min_age=16,
            max_age=40,
            competition_system=CompetitionSystem.ROUND_ROBIN.value,
            bracket_size=8,
            status=CategoryStatus.IN_PROGRESS.value,
            tournament_id=tournament_id,
            judge_panel_size=judge_panel_size,
            kata_flow_mode="INFORMAL",
        )
        session.add(cat)
        session.commit()
        session.refresh(cat)
        return cat


def _create_athlete(name: str, email: str) -> Athlete:
    """Helper: create a generic test athlete in the DB."""
    with rx.session() as session:
        athlete = Athlete(
            name=name,
            age=26,
            gender="MALE",
            email=email,
            belt_rank="Negro",
            is_active=True,
        )
        session.add(athlete)
        session.commit()
        session.refresh(athlete)
        return athlete


# ── mount_informal_category tests ──


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_mount_informal_category_sets_kata_mode(sample_tournament) -> None:
    """mount_informal_category sets kata_mode=INFORMAL and is_exhibition=False."""
    category = _create_informal_cat(sample_tournament.id)
    state = KataMatchState()

    await _event_fn(KataMatchState.mount_informal_category)(state, category.id)

    assert state.kata_mode == "INFORMAL"
    assert state.is_exhibition_mode is False


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_mount_informal_category_loads_roster(sample_tournament) -> None:
    """mount_informal_category populates roster and standings."""
    category = _create_informal_cat(sample_tournament.id)
    _create_athlete("Mount Athlete", "mount@test.local")
    state = KataMatchState()

    await _event_fn(KataMatchState.mount_informal_category)(state, category.id)

    assert state.informal_category_id == category.id
    assert len(state.informal_roster) == 1
    assert state.informal_roster[0]["name"] == "Mount Athlete"
    assert isinstance(state.informal_standings, list)


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_mount_informal_category_sets_judge_panel_size(sample_tournament) -> None:
    """mount_informal_category reads judge_panel_size from category."""
    category = _create_informal_cat(sample_tournament.id, judge_panel_size=3)
    _create_athlete("Panel Athlete", "panel@test.local")
    state = KataMatchState()

    await _event_fn(KataMatchState.mount_informal_category)(state, category.id)

    assert state.judge_panel_size == 3


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_informal_roster_labels_show_only_name(sample_tournament) -> None:
    """informal_roster_labels contains only athlete names, no 'ID - ' prefix."""
    category = _create_informal_cat(sample_tournament.id)
    _create_athlete("Maria", "maria@test.local")
    state = KataMatchState()

    await _event_fn(KataMatchState.mount_informal_category)(state, category.id)

    labels = state.informal_roster_labels
    assert len(labels) == 1
    assert labels[0] == "Maria"
    assert " - " not in labels[0]


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_informal_selected_athlete_label_shows_name(sample_tournament) -> None:
    """informal_selected_athlete_label returns athlete name only."""
    category = _create_informal_cat(sample_tournament.id)
    athlete = _create_athlete("Juan", "juan@test.local")
    state = KataMatchState()

    await _event_fn(KataMatchState.mount_informal_category)(state, category.id)

    label = state.informal_selected_athlete_label
    assert label == "Juan"
    assert " - " not in label


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_select_informal_athlete_by_name(sample_tournament) -> None:
    """select_informal_athlete_from_label matches by name, not ID prefix."""
    category = _create_informal_cat(sample_tournament.id)
    _create_athlete("Alpha", "alpha@test.local")
    athlete_beta = _create_athlete("Beta", "beta@test.local")
    state = KataMatchState()

    await _event_fn(KataMatchState.mount_informal_category)(state, category.id)

    await _event_fn(KataMatchState.select_informal_athlete_from_label)(state, "Beta")

    assert state.informal_selected_athlete_id == athlete_beta.id
    assert state.error_message == ""


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_finalize_category_without_category_errors(sample_tournament) -> None:
    """finalize_category errors when no informal category is active."""
    state = KataMatchState()
    state.informal_category_id = 0

    events = [event async for event in state.finalize_category()]

    assert state.error_message != ""


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_finalize_category_success(sample_tournament) -> None:
    """finalize_category succeeds when all athletes have been scored."""
    from kakumi_app.services.kata_informal_service import KataInformalService

    category = _create_informal_cat(sample_tournament.id)
    a1 = _create_athlete("F A1", "fa1@test.local")
    a2 = _create_athlete("F A2", "fa2@test.local")
    a3 = _create_athlete("F A3", "fa3@test.local")

    for athlete in (a1, a2, a3):
        KataInformalService.save_performance(
            category_id=category.id,
            athlete_id=athlete.id,
            judge_scores=[8.0, 8.0, 8.0, 8.0, 8.0],
        )

    state = KataMatchState()

    await _event_fn(KataMatchState.mount_informal_category)(state, category.id)

    events = [event async for event in state.finalize_category()]

    assert state.error_message == ""
    assert state.result_message != ""


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_mount_informal_category_invalid_id_handles_gracefully(
    sample_tournament,
) -> None:
    """mount_informal_category with non-existent category sets empty state."""
    state = KataMatchState()

    await _event_fn(KataMatchState.mount_informal_category)(state, 99999)

    assert state.informal_category_id == 0
    assert state.informal_roster == []


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_informal_roster_labels_multiple_athletes(sample_tournament) -> None:
    """All roster labels show name only regardless of athlete count."""
    category = _create_informal_cat(sample_tournament.id)
    _create_athlete("Alpha", "alpha2@test.local")
    _create_athlete("Beta", "beta2@test.local")
    _create_athlete("Gamma", "gamma@test.local")
    state = KataMatchState()

    await _event_fn(KataMatchState.mount_informal_category)(state, category.id)

    labels = state.informal_roster_labels
    assert len(labels) == 3
    for label in labels:
        assert " - " not in label, f"Label '{label}' should not contain ' - '"
    assert "Alpha" in labels
    assert "Beta" in labels
    assert "Gamma" in labels


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_select_informal_athlete_nonexistent_name_resets_selection(
    sample_tournament,
) -> None:
    """Selecting a non-existent name resets selected_athlete_id to 0."""
    category = _create_informal_cat(sample_tournament.id)
    _create_athlete("Only", "only@test.local")
    state = KataMatchState()

    await _event_fn(KataMatchState.mount_informal_category)(state, category.id)

    await _event_fn(KataMatchState.select_informal_athlete_from_label)(
        state, "NonExistent"
    )

    assert state.informal_selected_athlete_id == 0


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_finalize_category_errors_when_not_all_scored(
    sample_tournament,
) -> None:
    """finalize_category errors when some athletes lack scores."""
    from kakumi_app.services.kata_informal_service import KataInformalService

    category = _create_informal_cat(sample_tournament.id)
    a1 = _create_athlete("Scored Once", "scored1@test.local")
    a2 = _create_athlete("Scored Twice", "scored2@test.local")
    a3 = _create_athlete("Unscored", "noscore@test.local")

    # Score only 2 of 3 athletes
    KataInformalService.save_performance(
        category_id=category.id,
        athlete_id=a1.id,
        judge_scores=[8.0, 8.0, 8.0, 8.0, 8.0],
    )
    KataInformalService.save_performance(
        category_id=category.id,
        athlete_id=a2.id,
        judge_scores=[7.0, 7.0, 7.0, 7.0, 7.0],
    )

    state = KataMatchState()
    await _event_fn(KataMatchState.mount_informal_category)(state, category.id)

    events = [event async for event in state.finalize_category()]

    assert state.error_message != ""
    assert "sin puntuar" in state.error_message


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_finalize_informal_performance_auto_finalizes_when_all_scored(
    sample_tournament,
) -> None:
    """Scoring the last athlete auto-finalizes the category."""
    from kakumi_app.services.kata_informal_service import KataInformalService
    from kakumi_app.models.tournament_model import CategoryStatus

    category = _create_informal_cat(sample_tournament.id)
    a1 = _create_athlete("A1 AutoFinal", "af1@test.local")
    a2 = _create_athlete("A2 AutoFinal", "af2@test.local")
    a3 = _create_athlete("A3 AutoFinal", "af3@test.local")

    state = KataMatchState()
    await _event_fn(KataMatchState.mount_informal_category)(state, category.id)

    # Get roster order (randomized)
    roster_ids = [row["id"] for row in state.informal_roster if "id" in row]
    assert len(roster_ids) == 3
    first_id, second_id, third_id = roster_ids

    # Score first athlete
    state.informal_selected_athlete_id = first_id
    for slot in ("J1", "J2", "J3", "J4", "J5"):
        await _event_fn(KataMatchState.set_informal_judge_score)(state, slot, "8.0")
    events = [event async for event in state.finalize_match()]

    # Category should NOT be finalized yet — other athletes still unscored
    with rx.session() as session:
        db_cat = session.get(TournamentCategory, category.id)
        assert db_cat is not None
        assert db_cat.status != CategoryStatus.COMPLETED.value
    assert state.informal_selected_athlete_id == second_id

    # Score second athlete
    state.informal_selected_athlete_id = second_id
    for slot in ("J1", "J2", "J3", "J4", "J5"):
        await _event_fn(KataMatchState.set_informal_judge_score)(state, slot, "7.5")
    events = [event async for event in state.finalize_match()]

    with rx.session() as session:
        db_cat = session.get(TournamentCategory, category.id)
        assert db_cat is not None
        assert db_cat.status != CategoryStatus.COMPLETED.value
    assert state.informal_selected_athlete_id == third_id

    # Score third athlete — last -> auto-finalize
    state.informal_selected_athlete_id = third_id
    for slot in ("J1", "J2", "J3", "J4", "J5"):
        await _event_fn(KataMatchState.set_informal_judge_score)(state, slot, "7.0")
    events = [event async for event in state.finalize_match()]

    with rx.session() as session:
        db_cat = session.get(TournamentCategory, category.id)
        assert db_cat is not None
        assert db_cat.status == CategoryStatus.COMPLETED.value

    assert state.error_message == ""
    assert state.result_message != ""


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_finalize_informal_performance_advances_when_more_remain(
    sample_tournament,
) -> None:
    """Scoring an athlete when others remain advances to next athlete."""
    from kakumi_app.models.tournament_model import CategoryStatus

    category = _create_informal_cat(sample_tournament.id)
    a1 = _create_athlete("A1 Advance", "ad1@test.local")
    a2 = _create_athlete("A2 Advance", "ad2@test.local")
    a3 = _create_athlete("A3 Advance", "ad3@test.local")

    state = KataMatchState()
    await _event_fn(KataMatchState.mount_informal_category)(state, category.id)

    # Get first athlete from roster (order is random)
    first_id = state.informal_selected_athlete_id
    assert first_id > 0

    # Score the first athlete
    state.informal_selected_athlete_id = first_id
    for slot in ("J1", "J2", "J3", "J4", "J5"):
        await _event_fn(KataMatchState.set_informal_judge_score)(state, slot, "8.0")

    events = [event async for event in state.finalize_match()]

    # Should advance to next, NOT finalize
    with rx.session() as session:
        db_cat = session.get(TournamentCategory, category.id)
        assert db_cat is not None
        assert db_cat.status != CategoryStatus.COMPLETED.value

    # Should have advanced to a different athlete
    assert state.informal_selected_athlete_id != first_id
    assert state.informal_selected_athlete_id > 0
    assert state.error_message == ""
    assert state.result_message == ""
