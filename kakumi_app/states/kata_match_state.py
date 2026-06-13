"""Reflex state for live Kata match (tournament + exhibition)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import reflex as rx
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.kata_model import KataDecisionRule
from kakumi_app.models.referee_model import Referee, RefereeRole
from kakumi_app.models.tournament_model import (
    CategoryGender,
    Match,
    MatchStatus,
    Modality,
    Participant,
    TournamentCategory,
)
from kakumi_app.services.bracket_service import propagate_winner
from kakumi_app.services.kata_informal_service import KataInformalService
from kakumi_app.services.kata_scoring_service import KataScoringService
from kakumi_app.services.secondary_display_service import SecondaryDisplayService
from kakumi_app.utils import BELT_RANKS, BELT_RANK_ORDER


class KataMatchState(rx.State):
    """Live Kata orchestration state with exhibition/tournament split."""

    match_id: int = 0
    has_active_match: bool = False
    is_exhibition_mode: bool = False
    judge_panel_size: int = 5
    scoring_type: str = "STANDARD"
    decision_rule: str = KataDecisionRule.AVERAGE_WITH_DISCARD.value
    bunkai_required: bool = False
    aka_name: str = "ATLETA 1"
    ao_name: str = "ATLETA 2"
    judge_entries: dict[str, dict[str, str]] = {
        "J1": {"AKA": "", "AO": "", "vote": ""},
        "J2": {"AKA": "", "AO": "", "vote": ""},
        "J3": {"AKA": "", "AO": "", "vote": ""},
        "J4": {"AKA": "", "AO": "", "vote": ""},
        "J5": {"AKA": "", "AO": "", "vote": ""},
    }
    panel_complete: bool = False
    winner_participant: str = ""
    result_message: str = ""
    error_message: str = ""
    public_display_key: str = ""
    display_status: str = ""

    _judge_ids_by_slot: dict[str, int] = {}
    _allowed_decision_rules: tuple[str, str] = (
        KataDecisionRule.AVERAGE_WITH_DISCARD.value,
        KataDecisionRule.MAJORITY_BY_JUDGE.value,
    )
    kata_mode: str = "STANDARD"
    informal_category_id: int = 0
    informal_roster: list[dict[str, object]] = []
    informal_selected_athlete_id: int = 0
    informal_exhibition_participant_name: str = ""
    informal_judge_entries: dict[str, str] = {
        "J1": "",
        "J2": "",
        "J3": "",
        "J4": "",
        "J5": "",
    }
    informal_standings: list[dict[str, object]] = []

    @rx.var
    def is_informal_mode(self) -> bool:
        """Return whether scoreboard should use informal single-panel mode."""
        return self.kata_mode == "INFORMAL"

    @rx.var
    def informal_roster_labels(self) -> list[str]:
        """Return informal roster labels for select."""
        labels: list[str] = []
        for row in self.informal_roster:
            if "id" not in row or "name" not in row:
                continue
            labels.append(f"{self._coerce_int(row['id'])} - {str(row['name'])}")
        return labels

    @rx.var
    def informal_selected_athlete_label(self) -> str:
        """Return selected informal athlete label."""
        if self.informal_selected_athlete_id <= 0:
            return ""
        for row in self.informal_roster:
            if self._coerce_int(row.get("id")) == self.informal_selected_athlete_id:
                return f"{self._coerce_int(row['id'])} - {str(row['name'])}"
        return ""

    @rx.var
    def informal_current_athlete_label(self) -> str:
        """Return current informal athlete label."""
        if (
            self.is_informal_mode
            and self.is_exhibition_mode
            and self.informal_category_id == 0
        ):
            candidate = self.informal_exhibition_participant_name.strip()
            return candidate if candidate != "" else "ATLETA"
        return self.informal_selected_athlete_label

    @rx.var
    def judge_slots(self) -> list[str]:
        """Return configured judge slot labels in panel order."""
        return [f"J{index}" for index in range(1, self.judge_panel_size + 1)]

    @rx.var
    def is_flag_mode(self) -> bool:
        """Return whether category is in flag-vote mode."""
        return self.scoring_type == "FLAG"

    def _build_judge_entries(self, size: int) -> dict[str, dict[str, str]]:
        return {
            f"J{index}": {"AKA": "", "AO": "", "vote": ""}
            for index in range(1, size + 1)
        }

    @staticmethod
    def _coerce_int(raw_value: object, *, default: int = 0) -> int:
        if isinstance(raw_value, int):
            return raw_value
        if isinstance(raw_value, str):
            stripped = raw_value.strip()
            if stripped == "":
                return default
            try:
                return int(stripped)
            except ValueError:
                return default
        return default

    def _reset_state(self, *, exhibition_mode: bool) -> None:
        self.match_id = 0 if exhibition_mode else self.match_id
        self.has_active_match = False
        self.is_exhibition_mode = exhibition_mode
        self.kata_mode = "STANDARD"
        self.judge_panel_size = 5
        self.scoring_type = "STANDARD"
        self.decision_rule = KataDecisionRule.AVERAGE_WITH_DISCARD.value
        self.bunkai_required = False
        self.aka_name = "ATLETA 1"
        self.ao_name = "ATLETA 2"
        self.judge_entries = self._build_judge_entries(self.judge_panel_size)
        self.panel_complete = False
        self.winner_participant = ""
        self.result_message = ""
        self.error_message = ""
        self._judge_ids_by_slot = {}
        self.informal_category_id = 0
        self.informal_roster = []
        self.informal_selected_athlete_id = 0
        self.informal_exhibition_participant_name = ""
        self.informal_judge_entries = {"J1": "", "J2": "", "J3": "", "J4": "", "J5": ""}
        self.informal_standings = []

    def _build_informal_judge_entries(self) -> dict[str, str]:
        return {f"J{index}": "" for index in range(1, self.judge_panel_size + 1)}

    def _display_source_kind(self) -> str:
        return "EXHIBITION" if self.is_exhibition_mode else "TOURNAMENT"

    def _ensure_display_session(self) -> str:
        match_id = None if self.is_exhibition_mode else self.match_id
        display_session = SecondaryDisplayService.ensure_display_session(
            modality="KATA",
            source_kind=self._display_source_kind(),
            match_id=match_id,
        )
        self.public_display_key = display_session.display_key
        return self.public_display_key

    def _resolve_display_total(self, participant: str) -> str:
        if self.is_flag_mode:
            votes = 0
            for slot in self._panel_slots():
                if self.judge_entries[slot].get("vote") == participant:
                    votes += 1
            return str(votes)

        if self.kata_mode == "STANDARD":
            if self.decision_rule == KataDecisionRule.MAJORITY_BY_JUDGE.value:
                return "—"
            scores_sum = 0.0
            for slot in self._panel_slots():
                raw = self.judge_entries[slot].get(participant, "")
                if raw == "":
                    return "—"
                try:
                    scores_sum += float(raw)
                except ValueError:
                    return "—"
            return f"{scores_sum:.3f}"

        scores: list[float] = []
        for slot in self._panel_slots():
            raw = self.judge_entries[slot].get(participant, "")
            if raw == "":
                return "—"
            try:
                scores.append(float(raw))
            except ValueError:
                return "—"
        if len(scores) == 0:
            return "—"
        average = KataScoringService._average_with_optional_discard(scores)
        return f"{average:.3f}"

    def _resolve_majority_tally(self) -> str:
        if self.kata_mode != "STANDARD":
            return ""
        if self.is_flag_mode:
            return ""
        if self.decision_rule != KataDecisionRule.MAJORITY_BY_JUDGE.value:
            return ""
        if not self._resolve_panel_complete():
            return ""

        aka_votes, ao_votes, _, _ = self._count_numerical_votes()
        return f"AKA {aka_votes} - AO {ao_votes}"

    def _resolve_majority_vote_counts(self) -> tuple[int | None, int | None]:
        if self.kata_mode != "STANDARD":
            return None, None
        if self.is_flag_mode:
            return None, None
        if self.decision_rule != KataDecisionRule.MAJORITY_BY_JUDGE.value:
            return None, None
        if not self._resolve_panel_complete():
            return None, None

        aka_votes, ao_votes, _, _ = self._count_numerical_votes()
        return aka_votes, ao_votes

    def _build_informal_public_results(self) -> list[str]:
        results: list[str] = []
        for row in self.informal_standings:
            if (
                "rank" not in row
                or "athlete_name" not in row
                or "final_score" not in row
            ):
                continue
            results.append(
                f"{self._coerce_int(row['rank'])}. "
                f"{str(row['athlete_name'])} — {str(row['final_score'])}"
            )
        return results

    def _has_public_judge_input(self) -> bool:
        if self.kata_mode == "INFORMAL":
            return any(
                str(self.informal_judge_entries.get(slot, "")).strip() != ""
                for slot in self.judge_slots
            )

        if self.is_flag_mode:
            return any(
                self.judge_entries[slot].get("vote", "")
                in {Participant.AKA.value, Participant.AO.value}
                for slot in self._panel_slots()
            )

        return any(
            self.judge_entries[slot].get("AKA", "") != ""
            or self.judge_entries[slot].get("AO", "") != ""
            for slot in self._panel_slots()
        )

    def _build_public_judge_detail_lines(self) -> list[str]:
        if self.kata_mode == "INFORMAL":
            lines: list[str] = []
            for slot in self.judge_slots:
                score = str(self.informal_judge_entries.get(slot, "")).strip()
                if score != "":
                    lines.append(f"{slot}: {score}")
            return lines

        lines = []
        if self.is_flag_mode:
            for slot in self._panel_slots():
                vote = str(self.judge_entries[slot].get("vote", "")).strip()
                if vote != "":
                    lines.append(f"{slot}: {vote}")
            return lines

        for slot in self._panel_slots():
            aka = str(self.judge_entries[slot].get("AKA", "")).strip()
            ao = str(self.judge_entries[slot].get("AO", "")).strip()
            if aka == "" and ao == "":
                continue
            lines.append(f"{slot}: AKA {aka or '—'} / AO {ao or '—'}")
        return lines

    def _build_display_snapshot(self) -> dict[str, object]:
        judge_detail_visible = self._has_public_judge_input()
        majority_tally = self._resolve_majority_tally()
        majority_aka_votes, majority_ao_votes = self._resolve_majority_vote_counts()
        return {
            "modality": "KATA",
            "source_kind": self._display_source_kind(),
            "title": "Kata en vivo",
            "match_id": self.match_id if self.match_id > 0 else None,
            "is_exhibition_mode": self.is_exhibition_mode,
            "kata_mode": self.kata_mode,
            "judge_panel_size": self.judge_panel_size,
            "scoring_type": self.scoring_type,
            "decision_rule": self.decision_rule,
            "panel_complete": self.panel_complete,
            "winner": self.winner_participant,
            "result_message": self.result_message,
            "judge_detail_visible": judge_detail_visible,
            "judge_detail_lines": (
                self._build_public_judge_detail_lines() if judge_detail_visible else []
            ),
            "majority_tally_visible": majority_tally != "",
            "majority_tally": majority_tally,
            "majority_aka_votes": majority_aka_votes,
            "majority_ao_votes": majority_ao_votes,
            "informal": {
                "athlete_name": self.informal_current_athlete_label,
                "results": self._build_informal_public_results(),
            },
            "aka": {
                "name": self.aka_name,
                "total": self._resolve_display_total(Participant.AKA.value),
            },
            "ao": {
                "name": self.ao_name,
                "total": self._resolve_display_total(Participant.AO.value),
            },
        }

    def _is_viewer_connected(self) -> bool:
        try:
            app = rx.State._get_app()  # type: ignore[attr-defined]
            token = self.router.session.client_token
            socket_record = app._token_manager.token_to_socket.get(token)
            return socket_record is not None
        except Exception:
            return True

    def _publish_display_snapshot(self) -> None:
        # Operator-side snapshots are no-ops when viewer socket is gone.
        if not self._is_viewer_connected():
            return

        display_key = self.public_display_key or self._ensure_display_session()
        result = SecondaryDisplayService.publish_snapshot(
            display_key=display_key,
            snapshot=self._build_display_snapshot(),
        )
        self.display_status = "sync" if result is not None else "error"

    def _refresh_informal_standings(self) -> None:
        if self.informal_category_id <= 0:
            self.informal_standings = []
            return
        ranking = KataInformalService.rank_category(self.informal_category_id)
        name_by_id = {
            self._coerce_int(row["id"]): str(row["name"])
            for row in self.informal_roster
            if "id" in row and "name" in row
        }
        self.informal_standings = []
        for index, row in enumerate(ranking):
            athlete_id = self._coerce_int(row.get("athlete_id"))
            self.informal_standings.append(
                {
                    "rank": index + 1,
                    "athlete_id": athlete_id,
                    "athlete_name": name_by_id.get(athlete_id, "—"),
                    "final_score": f"{float(row['final_score']):.3f}",
                    "victory_points": self._coerce_int(
                        row.get("victory_points"),
                    ),
                    "needs_extra_kata": bool(row.get("needs_extra_kata", False)),
                }
            )

    def _advance_informal_next_athlete(self) -> None:
        roster_ids = [
            self._coerce_int(row["id"]) for row in self.informal_roster if "id" in row
        ]
        if not roster_ids:
            self.informal_selected_athlete_id = 0
            return
        if self.informal_selected_athlete_id not in roster_ids:
            self.informal_selected_athlete_id = roster_ids[0]
            return
        current_index = roster_ids.index(self.informal_selected_athlete_id)
        next_index = (current_index + 1) % len(roster_ids)
        self.informal_selected_athlete_id = roster_ids[next_index]

    def _load_informal_session(self, category_id: int) -> None:
        with rx.session() as session:
            category = session.get(TournamentCategory, category_id)
            if category is None:
                self.informal_category_id = 0
                self.informal_roster = []
                self.informal_selected_athlete_id = 0
                self.informal_judge_entries = self._build_informal_judge_entries()
                return

            query = select(Athlete).where(
                Athlete.age.between(category.min_age, category.max_age)
            )
            if category.gender == CategoryGender.MALE.value:
                query = query.where(Athlete.gender == "MALE")
            elif category.gender == CategoryGender.FEMALE.value:
                query = query.where(Athlete.gender == "FEMALE")

            athletes = session.exec(query.order_by(Athlete.name)).all()

            if category.min_belt_rank or category.max_belt_rank:
                min_idx = BELT_RANK_ORDER.get(category.min_belt_rank, 0)
                max_idx = BELT_RANK_ORDER.get(
                    category.max_belt_rank, len(BELT_RANKS) - 1
                )
                athletes = [
                    athlete
                    for athlete in athletes
                    if athlete.belt_rank
                    and min_idx <= BELT_RANK_ORDER.get(athlete.belt_rank, -1) <= max_idx
                ]

        self.informal_category_id = category_id
        self.informal_roster = [
            {"id": athlete.id, "name": athlete.name} for athlete in athletes
        ]
        self.informal_selected_athlete_id = (
            self._coerce_int(self.informal_roster[0]["id"])
            if len(self.informal_roster) > 0
            else 0
        )
        self.informal_judge_entries = self._build_informal_judge_entries()
        self._refresh_informal_standings()

    def _resolve_exhibition_informal_category_id(self) -> int:
        with rx.session() as session:
            category = session.exec(
                select(TournamentCategory)
                .where(TournamentCategory.modality == Modality.KATA_INDIVIDUAL.value)
                .order_by(TournamentCategory.id)
            ).first()
        if category is None:
            raise ValueError("No hay categoría disponible para modo informal")
        return int(category.id)

    def _route_params(self) -> dict[str, Any]:
        try:
            return dict(self.router.page.params)
        except Exception:
            page = getattr(self.router, "_page", None)
            return dict(getattr(page, "params", {}) or {})

    def _parse_match_id(self) -> int:
        params = self._route_params()
        raw_match_id = params.get("match_id", params.get("id"))
        if raw_match_id in (None, ""):
            raise ValueError("ID de encuentro inválido")
        return int(raw_match_id)

    def _resolve_athlete_name(self, athlete_id: int | None) -> str:
        if athlete_id is None:
            return "ATLETA"
        with rx.session() as session:
            athlete = session.get(Athlete, athlete_id)
            if athlete is None:
                return "ATLETA"
            return athlete.name

    def _resolve_panel_size(self, panel_size: int | None) -> int:
        size = int(panel_size or 5)
        if size not in {3, 5}:
            raise ValueError("Panel de jueces inválido")
        return size

    def _panel_slots(self) -> Iterable[str]:
        return (f"J{index}" for index in range(1, self.judge_panel_size + 1))

    def _resolve_panel_complete(self) -> bool:
        if self.is_flag_mode:
            return all(
                self.judge_entries[slot].get("vote")
                in {
                    Participant.AKA.value,
                    Participant.AO.value,
                }
                for slot in self._panel_slots()
            )

        for slot in self._panel_slots():
            aka_raw = self.judge_entries[slot].get("AKA", "")
            ao_raw = self.judge_entries[slot].get("AO", "")
            if aka_raw == "" or ao_raw == "":
                return False
            try:
                float(aka_raw)
                float(ao_raw)
            except ValueError:
                return False
        return True

    def _count_numerical_votes(self) -> tuple[int, int, list[float], list[float]]:
        aka_votes = 0
        ao_votes = 0
        aka_scores: list[float] = []
        ao_scores: list[float] = []

        for slot in self._panel_slots():
            aka_score = float(self.judge_entries[slot]["AKA"])
            ao_score = float(self.judge_entries[slot]["AO"])
            aka_scores.append(aka_score)
            ao_scores.append(ao_score)
            if aka_score > ao_score:
                aka_votes += 1
            elif ao_score > aka_score:
                ao_votes += 1

        return aka_votes, ao_votes, aka_scores, ao_scores

    def _resolve_flag_exhibition_result(self) -> tuple[str, str]:
        aka_votes = 0
        ao_votes = 0
        for slot in self._panel_slots():
            vote = self.judge_entries[slot]["vote"]
            if vote == Participant.AKA.value:
                aka_votes += 1
            elif vote == Participant.AO.value:
                ao_votes += 1

        if aka_votes > ao_votes:
            return Participant.AKA.value, "Ganador por mayoría de banderas"
        if ao_votes > aka_votes:
            return Participant.AO.value, "Ganador por mayoría de banderas"
        return "", "Empate - requiere kata extra"

    def _resolve_numerical_exhibition_result(self) -> tuple[str, str]:
        aka_votes, ao_votes, aka_scores, ao_scores = self._count_numerical_votes()
        if self.decision_rule == KataDecisionRule.MAJORITY_BY_JUDGE.value:
            if aka_votes > ao_votes:
                return Participant.AKA.value, "Ganador por mayoría de jueces"
            if ao_votes > aka_votes:
                return Participant.AO.value, "Ganador por mayoría de jueces"
            return "", "Empate - requiere kata extra"

        aka_average = KataScoringService._average_with_optional_discard(aka_scores)
        ao_average = KataScoringService._average_with_optional_discard(ao_scores)
        if aka_average > ao_average:
            return Participant.AKA.value, "Ganador por promedio"
        if ao_average > aka_average:
            return Participant.AO.value, "Ganador por promedio"
        return "", "Empate - requiere kata extra"

    def _resolve_exhibition_result(self) -> tuple[str, str]:
        if self.is_flag_mode:
            return self._resolve_flag_exhibition_result()
        return self._resolve_numerical_exhibition_result()

    def _save_tournament_scores(self) -> None:
        with rx.session() as session:
            match = session.get(Match, self.match_id)
            if match is None:
                raise ValueError("Encuentro no encontrado")

            if self.is_flag_mode:
                for slot in self._panel_slots():
                    judge_id = self._judge_ids_by_slot[slot]
                    KataScoringService.record_flag_vote(
                        match_id=self.match_id,
                        judge_id=judge_id,
                        flag_vote=self.judge_entries[slot]["vote"],
                    )
            else:
                for slot in self._panel_slots():
                    judge_id = self._judge_ids_by_slot[slot]
                    KataScoringService.record_numerical_score(
                        match_id=self.match_id,
                        judge_id=judge_id,
                        participant=Participant.AKA.value,
                        performer_id=match.aka_id,
                        team_id=match.aka_team_id,
                        score=float(self.judge_entries[slot]["AKA"]),
                    )
                    KataScoringService.record_numerical_score(
                        match_id=self.match_id,
                        judge_id=judge_id,
                        participant=Participant.AO.value,
                        performer_id=match.ao_id,
                        team_id=match.ao_team_id,
                        score=float(self.judge_entries[slot]["AO"]),
                    )

        KataScoringService.apply_bunkai_mode(self.match_id)
        result = KataScoringService.calculate_match_winner(self.match_id)
        KataScoringService.assign_victory_points(
            match_id=self.match_id,
            winner_participant=result.winner,
            aka_votes=result.aka_votes,
            ao_votes=result.ao_votes,
        )
        with rx.session() as session:
            match = session.get(Match, self.match_id)
            if match is None:
                raise ValueError("Encuentro no encontrado")
            if result.winner == Participant.AKA.value:
                match.winner_id = match.aka_id
            elif result.winner == Participant.AO.value:
                match.winner_id = match.ao_id
            else:
                match.winner_id = None
            match.aka_score = int(result.aka_votes)
            match.ao_score = int(result.ao_votes)
            match.status = MatchStatus.COMPLETED.value
            session.add(match)
            session.commit()

            propagate_winner(session, match)
            session.commit()

        self.winner_participant = str(result.winner or "")
        self.result_message = result.message

    def _set_numerical_entry(
        self,
        judge_slot: str,
        participant: str,
        value: str,
    ) -> None:
        if judge_slot not in self.judge_entries:
            return
        if participant not in {Participant.AKA.value, Participant.AO.value}:
            return
        next_entries = {slot: dict(entry) for slot, entry in self.judge_entries.items()}
        next_entries[judge_slot][participant] = value.strip()
        self.judge_entries = next_entries
        self.panel_complete = self._resolve_panel_complete()

    @rx.event
    async def enable_exhibition_mode(self) -> None:
        self._reset_state(exhibition_mode=True)
        self._publish_display_snapshot()

    @rx.event
    async def set_kata_mode(self, mode: str) -> None:
        """Set exhibition Kata flow mode."""
        if mode not in {"STANDARD", "INFORMAL"}:
            return
        self.kata_mode = mode
        self.error_message = ""
        self.winner_participant = ""
        self.result_message = ""
        if mode == "INFORMAL":
            if self.is_exhibition_mode:
                self.informal_category_id = 0
                self.informal_roster = []
                self.informal_selected_athlete_id = 0
                self.informal_exhibition_participant_name = ""
                self.informal_judge_entries = self._build_informal_judge_entries()
                self.informal_standings = []
            elif self.informal_category_id > 0:
                self._load_informal_session(self.informal_category_id)
        self._publish_display_snapshot()

    @rx.event
    async def load_match(self) -> None:
        self.error_message = ""
        self.winner_participant = ""
        self.result_message = ""
        self.is_exhibition_mode = False
        try:
            match_id = self._parse_match_id()
        except ValueError:
            self._reset_state(exhibition_mode=False)
            self.error_message = "ID de encuentro inválido"
            return

        with rx.session() as session:
            match = session.get(Match, match_id)
            if match is None or match.category is None:
                self._reset_state(exhibition_mode=False)
                self.error_message = "Encuentro no encontrado"
                return

            panel_size = self._resolve_panel_size(match.category.judge_panel_size)
            self.match_id = match.id
            self.has_active_match = True
            self.judge_panel_size = panel_size
            self.scoring_type = str(match.category.scoring_type or "STANDARD")
            self.kata_mode = str(getattr(match.category, "kata_flow_mode", "STANDARD"))
            self.decision_rule = str(
                match.category.kata_decision_rule
                or KataDecisionRule.AVERAGE_WITH_DISCARD.value
            )
            self.bunkai_required = bool(match.bunkai_required)
            self.aka_name = self._resolve_athlete_name(match.aka_id)
            self.ao_name = self._resolve_athlete_name(match.ao_id)
            self.judge_entries = self._build_judge_entries(panel_size)
            self.panel_complete = False

            judges = session.exec(
                select(Referee)
                .where(Referee.role == RefereeRole.JUDGE.value)
                .order_by(Referee.id.asc())
            ).all()
            self._judge_ids_by_slot = {
                f"J{index + 1}": judge.id
                for index, judge in enumerate(judges[:panel_size])
            }

            if self.kata_mode == "INFORMAL":
                self._load_informal_session(match.category_id)
        self._publish_display_snapshot()

    @rx.event
    async def set_panel_size(self, size: int) -> None:
        resolved = self._resolve_panel_size(int(size))
        self.judge_panel_size = resolved
        self.judge_entries = self._build_judge_entries(resolved)
        self.panel_complete = False
        self.winner_participant = ""
        self.result_message = ""
        self._publish_display_snapshot()

    @rx.event
    async def set_judge_score(
        self,
        judge_slot: str,
        participant: str,
        value: str,
    ) -> None:
        self.error_message = ""
        self._set_numerical_entry(judge_slot, participant, value)
        self._publish_display_snapshot()

    @rx.event
    def set_decision_rule(self, decision_rule: str) -> None:
        if not self.is_exhibition_mode:
            return
        if decision_rule not in self._allowed_decision_rules:
            return
        self.decision_rule = decision_rule
        self.winner_participant = ""
        self.result_message = ""
        self.error_message = ""
        self._publish_display_snapshot()

    @rx.event
    async def set_flag_vote(self, judge_slot: str, vote: str) -> None:
        self.error_message = ""
        if judge_slot not in self.judge_entries:
            return
        if vote not in {Participant.AKA.value, Participant.AO.value}:
            return
        next_entries = {slot: dict(entry) for slot, entry in self.judge_entries.items()}
        next_entries[judge_slot]["vote"] = vote
        self.judge_entries = next_entries
        self.panel_complete = self._resolve_panel_complete()
        self._publish_display_snapshot()

    @rx.event
    async def reset_entries(self) -> None:
        if self.is_informal_mode:
            self.informal_judge_entries = self._build_informal_judge_entries()
            if self.is_exhibition_mode and self.informal_category_id == 0:
                self.informal_exhibition_participant_name = ""
        else:
            self.judge_entries = self._build_judge_entries(self.judge_panel_size)
        self.panel_complete = False
        self.winner_participant = ""
        self.result_message = ""
        self.error_message = ""
        self._publish_display_snapshot()

    @rx.event
    async def select_informal_athlete_from_label(self, label: str) -> None:
        """Set current informal athlete from roster label."""
        athlete_id = str(label).split(" - ")[0]
        self.informal_selected_athlete_id = int(athlete_id)
        self.informal_judge_entries = self._build_informal_judge_entries()
        self.error_message = ""
        self._publish_display_snapshot()

    @rx.event
    async def set_informal_judge_score(self, judge_slot: str, value: str) -> None:
        """Set one informal judge score input."""
        if judge_slot not in self.informal_judge_entries:
            return
        updated = dict(self.informal_judge_entries)
        updated[judge_slot] = value.strip()
        self.informal_judge_entries = updated
        self._publish_display_snapshot()

    @rx.event
    async def set_informal_exhibition_participant_name(self, value: str) -> None:
        """Set optional participant label for free exhibition informal run."""
        self.informal_exhibition_participant_name = value
        self._publish_display_snapshot()

    def _finalize_informal_exhibition_free(self) -> None:
        """Persist one free-sequence exhibition informal run in-memory."""
        scores: list[float] = []
        for slot in self.judge_slots:
            raw = self.informal_judge_entries.get(slot, "")
            if raw == "":
                raise ValueError("Panel incompleto")
            scores.append(float(raw))

        run_name = self.informal_exhibition_participant_name.strip() or "ATLETA"
        final_score = KataInformalService._compute_score(scores).final_score
        next_rows = [dict(row) for row in self.informal_standings]
        next_rows.append(
            {
                "rank": 0,
                "athlete_id": 0,
                "athlete_name": run_name,
                "final_score": f"{final_score:.3f}",
                "victory_points": 0,
                "needs_extra_kata": False,
            }
        )
        sorted_rows = sorted(
            next_rows,
            key=lambda row: float(str(row["final_score"])),
            reverse=True,
        )
        self.informal_standings = [
            {**row, "rank": index + 1} for index, row in enumerate(sorted_rows)
        ]
        self.informal_judge_entries = self._build_informal_judge_entries()
        self.informal_exhibition_participant_name = ""

    def _finalize_informal_performance(self) -> None:
        if self.is_exhibition_mode and self.informal_category_id == 0:
            self._finalize_informal_exhibition_free()
            return

        if self.informal_category_id <= 0:
            raise ValueError("Categoría informal no disponible")
        if self.informal_selected_athlete_id <= 0:
            raise ValueError("Selecciona un atleta")

        scores: list[float] = []
        for slot in self.judge_slots:
            raw = self.informal_judge_entries.get(slot, "")
            if raw == "":
                raise ValueError("Panel incompleto")
            scores.append(float(raw))

        KataInformalService.save_performance(
            category_id=self.informal_category_id,
            athlete_id=self.informal_selected_athlete_id,
            judge_scores=scores,
        )
        self._refresh_informal_standings()
        self.informal_judge_entries = self._build_informal_judge_entries()
        self._advance_informal_next_athlete()

    @rx.event
    async def finalize_match(self):
        self.error_message = ""
        self.winner_participant = ""
        self.result_message = ""
        if self.is_informal_mode:
            try:
                self._finalize_informal_performance()
            except ValueError as error:
                self.error_message = str(error)
                yield rx.toast.error(str(error))
            self._publish_display_snapshot()
            return

        self.panel_complete = self._resolve_panel_complete()
        if not self.panel_complete:
            self.error_message = "Panel incompleto"
            yield rx.toast.error("Panel incompleto")
            return

        if self.is_exhibition_mode:
            winner, message = self._resolve_exhibition_result()
            self.winner_participant = winner
            self.result_message = message
            self._publish_display_snapshot()
            return

        if self.match_id <= 0:
            self.error_message = "Encuentro no encontrado"
            yield rx.toast.error("Encuentro no encontrado")
            return

        if len(self._judge_ids_by_slot) != self.judge_panel_size:
            self.error_message = "Panel de jueces no disponible"
            yield rx.toast.error("Panel de jueces no disponible")
            return

        try:
            self._save_tournament_scores()
        except Exception as error:
            self.error_message = str(error)
            yield rx.toast.error(str(error))
        self._publish_display_snapshot()
