"""Tests for KataMatchState exhibition/tournament live flow."""

from __future__ import annotations

import pytest
import reflex as rx
from reflex.istate.data import PageData
from sqlmodel import select

from kakumi_app.models.kata_model import KataJudgeScore
from kakumi_app.models.tournament_model import Match, MatchStatus
from kakumi_app.services.kata_scoring_service import KataScoringService
from kakumi_app.states.kata_match_state import KataMatchState


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

    await KataMatchState.enable_exhibition_mode.fn(state)

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

    await KataMatchState.enable_exhibition_mode.fn(state)

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

    await KataMatchState.load_match.fn(state)

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
    await KataMatchState.enable_exhibition_mode.fn(state)

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
    await KataMatchState.enable_exhibition_mode.fn(state)
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
    await KataMatchState.enable_exhibition_mode.fn(state)
    await KataMatchState.set_panel_size.fn(state, 3)
    await KataMatchState.set_judge_score.fn(state, "J1", "AKA", "9.0")
    await KataMatchState.set_judge_score.fn(state, "J1", "AO", "8.0")
    await KataMatchState.set_judge_score.fn(state, "J2", "AKA", "9.0")
    await KataMatchState.set_judge_score.fn(state, "J2", "AO", "8.0")
    await KataMatchState.set_judge_score.fn(state, "J3", "AKA", "7.0")
    await KataMatchState.set_judge_score.fn(state, "J3", "AO", "9.9")

    default_events = [event async for event in state.finalize_match()]

    assert default_events == []
    assert state.winner_participant == "AO"

    KataMatchState.set_decision_rule.fn(state, "majority-by-judge")
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
    await KataMatchState.load_match.fn(state)
    category_rule = state.decision_rule

    KataMatchState.set_decision_rule.fn(state, "majority-by-judge")

    assert state.decision_rule == category_rule


@pytest.mark.asyncio
@pytest.mark.anyio
async def test_finalize_tournament_rejects_incomplete_panel(
    kata_match,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = KataMatchState()
    _set_match_route_param(state, kata_match.id)
    await KataMatchState.load_match.fn(state)

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
    await KataMatchState.load_match.fn(state)
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
    await KataMatchState.load_match.fn(state)
    await KataMatchState.set_flag_vote.fn(state, "J1", "AKA")
    await KataMatchState.set_flag_vote.fn(state, "J2", "AKA")
    await KataMatchState.set_flag_vote.fn(state, "J3", "AO")

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
    await KataMatchState.load_match.fn(state)
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

    await KataMatchState.enable_exhibition_mode.fn(state)

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
async def test_finalize_exhibition_informal_saves_and_advances_participant(
) -> None:
    state = KataMatchState()
    await KataMatchState.enable_exhibition_mode.fn(state)
    await KataMatchState.set_kata_mode.fn(state, "INFORMAL")
    await KataMatchState.set_informal_exhibition_participant_name.fn(state, "Lucía")

    for slot in ("J1", "J2", "J3", "J4", "J5"):
        await KataMatchState.set_informal_judge_score.fn(state, slot, "8.2")

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
async def test_exhibition_informal_works_without_category_and_uses_fallback_name() -> None:
    state = KataMatchState()
    await KataMatchState.enable_exhibition_mode.fn(state)

    await KataMatchState.set_kata_mode.fn(state, "INFORMAL")

    assert state.kata_mode == "INFORMAL"
    assert state.error_message == ""
    assert state.informal_category_id == 0
    assert state.informal_current_athlete_label == "ATLETA"

    for slot in ("J1", "J2", "J3", "J4", "J5"):
        await KataMatchState.set_informal_judge_score.fn(state, slot, "8.0")

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

    await KataMatchState.load_match.fn(state)

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

    await KataMatchState.load_match.fn(state)

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
    await KataMatchState.enable_exhibition_mode.fn(state)

    calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        "kakumi_app.states.kata_match_state.SecondaryDisplayService.publish_snapshot",
        lambda *, display_key, snapshot: calls.append(
            {"display_key": display_key, "snapshot": snapshot}
        ),
    )

    await KataMatchState.reset_entries.fn(state)

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
    await KataMatchState.enable_exhibition_mode.fn(state)
    await KataMatchState.set_panel_size.fn(state, 3)
    state.kata_mode = "STANDARD"
    state.decision_rule = "average-with-discard"

    await KataMatchState.set_judge_score.fn(state, "J1", "AKA", "9.0")
    await KataMatchState.set_judge_score.fn(state, "J1", "AO", "8.0")
    await KataMatchState.set_judge_score.fn(state, "J2", "AKA", "9.0")
    await KataMatchState.set_judge_score.fn(state, "J2", "AO", "8.0")
    await KataMatchState.set_judge_score.fn(state, "J3", "AKA", "7.0")
    await KataMatchState.set_judge_score.fn(state, "J3", "AO", "9.9")

    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        "kakumi_app.states.kata_match_state.SecondaryDisplayService.publish_snapshot",
        lambda *, display_key, snapshot: calls.append(snapshot),
    )

    await KataMatchState.set_judge_score.fn(state, "J3", "AO", "9.9")
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
    await KataMatchState.enable_exhibition_mode.fn(state)
    state.kata_mode = "STANDARD"

    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        "kakumi_app.states.kata_match_state.SecondaryDisplayService.publish_snapshot",
        lambda *, display_key, snapshot: calls.append(snapshot),
    )

    await KataMatchState.reset_entries.fn(state)
    await KataMatchState.set_judge_score.fn(state, "J1", "AKA", "8.4")

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
    await KataMatchState.enable_exhibition_mode.fn(state)
    await KataMatchState.set_kata_mode.fn(state, "INFORMAL")

    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        "kakumi_app.states.kata_match_state.SecondaryDisplayService.publish_snapshot",
        lambda *, display_key, snapshot: calls.append(snapshot),
    )

    await KataMatchState.reset_entries.fn(state)
    await KataMatchState.set_informal_judge_score.fn(state, "J2", "8.7")

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
    await KataMatchState.enable_exhibition_mode.fn(state)
    await KataMatchState.set_kata_mode.fn(state, "INFORMAL")
    await KataMatchState.set_informal_exhibition_participant_name.fn(state, "Lucía")

    for slot in ("J1", "J2", "J3", "J4", "J5"):
        await KataMatchState.set_informal_judge_score.fn(state, slot, "8.2")

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
    await KataMatchState.enable_exhibition_mode.fn(state)
    await KataMatchState.set_panel_size.fn(state, 5)
    state.kata_mode = "STANDARD"
    state.decision_rule = "majority-by-judge"

    await KataMatchState.set_judge_score.fn(state, "J1", "AKA", "8.0")
    await KataMatchState.set_judge_score.fn(state, "J1", "AO", "7.0")
    await KataMatchState.set_judge_score.fn(state, "J2", "AKA", "8.1")
    await KataMatchState.set_judge_score.fn(state, "J2", "AO", "7.1")
    await KataMatchState.set_judge_score.fn(state, "J3", "AKA", "8.2")
    await KataMatchState.set_judge_score.fn(state, "J3", "AO", "7.2")
    await KataMatchState.set_judge_score.fn(state, "J4", "AKA", "7.0")
    await KataMatchState.set_judge_score.fn(state, "J4", "AO", "8.0")
    await KataMatchState.set_judge_score.fn(state, "J5", "AKA", "7.1")
    await KataMatchState.set_judge_score.fn(state, "J5", "AO", "8.1")

    snapshot = state._build_display_snapshot()

    assert snapshot["majority_tally_visible"] is True
    assert snapshot["majority_tally"] == "AKA 3 - AO 2"
    assert snapshot["majority_aka_votes"] == 3
    assert snapshot["majority_ao_votes"] == 2
