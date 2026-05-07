"""Reflex state for live Kata match (tournament + exhibition)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import reflex as rx
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.kata_model import KataDecisionRule
from kakumi_app.models.referee_model import Referee, RefereeRole
from kakumi_app.models.tournament_model import Match, MatchStatus, Participant
from kakumi_app.services.kata_scoring_service import KataScoringService


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

    _judge_ids_by_slot: dict[str, int] = {}
    _allowed_decision_rules: tuple[str, str] = (
        KataDecisionRule.AVERAGE_WITH_DISCARD.value,
        KataDecisionRule.MAJORITY_BY_JUDGE.value,
    )

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

    def _reset_state(self, *, exhibition_mode: bool) -> None:
        self.match_id = 0 if exhibition_mode else self.match_id
        self.has_active_match = False
        self.is_exhibition_mode = exhibition_mode
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
                self.judge_entries[slot].get("vote") in {
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
        next_entries = {
            slot: dict(entry) for slot, entry in self.judge_entries.items()
        }
        next_entries[judge_slot][participant] = value.strip()
        self.judge_entries = next_entries
        self.panel_complete = self._resolve_panel_complete()

    @rx.event
    async def enable_exhibition_mode(self) -> None:
        self._reset_state(exhibition_mode=True)

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

    @rx.event
    async def set_panel_size(self, size: int) -> None:
        resolved = self._resolve_panel_size(int(size))
        self.judge_panel_size = resolved
        self.judge_entries = self._build_judge_entries(resolved)
        self.panel_complete = False
        self.winner_participant = ""
        self.result_message = ""

    @rx.event
    async def set_judge_score(
        self,
        judge_slot: str,
        participant: str,
        value: str,
    ) -> None:
        self.error_message = ""
        self._set_numerical_entry(judge_slot, participant, value)

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

    @rx.event
    async def set_flag_vote(self, judge_slot: str, vote: str) -> None:
        self.error_message = ""
        if judge_slot not in self.judge_entries:
            return
        if vote not in {Participant.AKA.value, Participant.AO.value}:
            return
        next_entries = {
            slot: dict(entry) for slot, entry in self.judge_entries.items()
        }
        next_entries[judge_slot]["vote"] = vote
        self.judge_entries = next_entries
        self.panel_complete = self._resolve_panel_complete()

    @rx.event
    async def reset_entries(self) -> None:
        self.judge_entries = self._build_judge_entries(self.judge_panel_size)
        self.panel_complete = False
        self.winner_participant = ""
        self.result_message = ""
        self.error_message = ""

    @rx.event
    async def finalize_match(self):
        self.error_message = ""
        self.winner_participant = ""
        self.result_message = ""
        self.panel_complete = self._resolve_panel_complete()
        if not self.panel_complete:
            self.error_message = "Panel incompleto"
            yield rx.toast.error("Panel incompleto")
            return

        if self.is_exhibition_mode:
            winner, message = self._resolve_exhibition_result()
            self.winner_participant = winner
            self.result_message = message
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
