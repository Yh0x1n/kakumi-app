"""Reflex state for managing a Kumite match in progress.

Handles timer pause/resume around penalty operations and
syncs with the backend scoring service.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any, Optional

import reflex as rx
from sqlmodel import Session, select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.tournament_model import (
    Match,
    MatchActionLog,
    Participant,
    Penalty,
    PenaltyType,
    TournamentCategory,
)
from kakumi_app.services import kumite_scoring_service
from kakumi_app.services.kumite_scoring_service import KumiteScoringService
from kakumi_app.services.exceptions import (
    AthleteSchedulingConflictError,
    PenaltyEscalationError,
    PenaltyRemovalNotAllowedError,
)


class KumiteMatchState(rx.State):
    """State that coordinates penalty actions and local timer sync.

    Public attributes are JSON-serializable for Reflex frontend synchronization.
    Variables with underscore prefix are backend-only internal flags.
    """

    # Public vars (synced to frontend)
    match_id: int = 0
    has_active_match: bool = False
    is_exhibition_mode: bool = False
    timer_paused: bool = False
    timer_running: bool = False
    timer_seconds: int = 180
    timer_base_seconds: int = 180
    error_message: str = ""
    last_action_label: str = ""

    aka_score: int = 0
    ao_score: int = 0
    aka_name: str = "ATLETA 1"
    ao_name: str = "ATLETA 2"
    aka_senshu: bool = False
    ao_senshu: bool = False

    aka_penalty_slots: dict[str, bool] = {
        "C1": False,
        "C2": False,
        "C3": False,
        "HC": False,
        "H": False,
    }
    ao_penalty_slots: dict[str, bool] = {
        "C1": False,
        "C2": False,
        "C3": False,
        "HC": False,
        "H": False,
    }

    last_penalty_aka: str = ""
    last_penalty_ao: str = ""

    # Backend-only vars
    _processing: bool = False
    _exhibition_undo_stack: list[dict[str, Any]] = []
    _timer_loop_active: bool = False

    def _reset_scoreboard(self, *, exhibition_mode: bool = True) -> None:
        """Reset synced scoreboard vars to default safe state."""
        self.has_active_match = False
        self.is_exhibition_mode = exhibition_mode
        self.aka_score = 0
        self.ao_score = 0
        self.aka_name = "ATLETA 1"
        self.ao_name = "ATLETA 2"
        self.aka_senshu = False
        self.ao_senshu = False
        self.timer_running = False
        self._timer_loop_active = False
        self.timer_base_seconds = 180
        self.timer_seconds = 180
        self.aka_penalty_slots = self._build_penalty_slots([])
        self.ao_penalty_slots = self._build_penalty_slots([])
        self._exhibition_undo_stack = []

    def _exhibition_snapshot(self) -> dict[str, Any]:
        """Capture local exhibition state for one-step undo stack."""
        return {
            "aka_score": self.aka_score,
            "ao_score": self.ao_score,
            "aka_penalty_slots": dict(self.aka_penalty_slots),
            "ao_penalty_slots": dict(self.ao_penalty_slots),
            "aka_senshu": self.aka_senshu,
            "ao_senshu": self.ao_senshu,
        }

    def _push_exhibition_snapshot(self) -> None:
        """Store snapshot before exhibition mutation."""
        self._exhibition_undo_stack.append(self._exhibition_snapshot())

    def _apply_exhibition_score(self, participant: str, score_type: str) -> None:
        """Apply local score mutation for exhibition mode."""
        self._push_exhibition_snapshot()
        points_by_type = {"YUKO": 1, "WAZA_ARI": 2, "IPPON": 3}
        points = points_by_type.get(score_type, 0)
        if participant == Participant.AKA.value:
            self.aka_score += points
        else:
            self.ao_score += points
        self.last_action_label = f"EXH-SCORE:{participant}:{score_type}"

    def _apply_exhibition_manual_senshu(self, participant: str) -> None:
        """Set manual senshu locally for exhibition flow."""
        self._push_exhibition_snapshot()
        if participant == Participant.AKA.value:
            self.aka_senshu = True
            self.ao_senshu = False
        elif participant == Participant.AO.value:
            self.ao_senshu = True
            self.aka_senshu = False
        self.last_action_label = f"EXH-SENSHU-SET:{participant}"

    def _revoke_exhibition_manual_senshu(self, participant: str) -> None:
        """Revoke manual senshu locally for exhibition flow."""
        self._push_exhibition_snapshot()
        if participant == Participant.AKA.value:
            self.aka_senshu = False
        elif participant == Participant.AO.value:
            self.ao_senshu = False
        self.last_action_label = f"EXH-SENSHU-REVOKE:{participant}"

    def _next_exhibition_penalty_slots(
        self,
        slots: dict[str, bool],
    ) -> dict[str, bool]:
        """Compute next cumulative penalty step for exhibition mode."""
        next_slots = dict(slots)
        for key in ("C1", "C2", "C3", "HC", "H"):
            if not next_slots[key]:
                next_slots[key] = True
                break
        return next_slots

    def _apply_exhibition_penalty(self, participant: str) -> None:
        """Apply local cumulative penalty in exhibition mode."""
        self._push_exhibition_snapshot()
        if participant == Participant.AKA.value:
            self.aka_penalty_slots = self._next_exhibition_penalty_slots(
                self.aka_penalty_slots,
            )
        else:
            self.ao_penalty_slots = self._next_exhibition_penalty_slots(
                self.ao_penalty_slots,
            )
        self.last_action_label = f"EXH-PENALTY:{participant}"

    def _undo_exhibition_action(self) -> None:
        """Rollback latest exhibition mutation snapshot."""
        if not self._exhibition_undo_stack:
            return
        snapshot = self._exhibition_undo_stack.pop()
        self.aka_score = int(snapshot["aka_score"])
        self.ao_score = int(snapshot["ao_score"])
        self.aka_penalty_slots = dict(snapshot["aka_penalty_slots"])
        self.ao_penalty_slots = dict(snapshot["ao_penalty_slots"])
        self.aka_senshu = bool(snapshot["aka_senshu"])
        self.ao_senshu = bool(snapshot["ao_senshu"])
        self.last_action_label = "EXH-UNDO"

    @rx.var
    def timer_formatted(self) -> str:
        """Render countdown as mm:ss."""
        minutes = max(self.timer_seconds, 0) // 60
        seconds = max(self.timer_seconds, 0) % 60
        return f"{minutes:02d}:{seconds:02d}"

    def _route_params(self) -> dict[str, Any]:
        """Safely resolve route params from router state."""
        try:
            return dict(self.router.page.params)
        except Exception:
            page = getattr(self.router, "_page", None)
            return dict(getattr(page, "params", {}) or {})

    def _parse_match_id(self) -> int:
        """Parse match id from route params."""
        params = self._route_params()
        raw_match_id = params.get("match_id", params.get("id"))
        if raw_match_id in (None, ""):
            raise ValueError("ID de encuentro inválido")
        return int(raw_match_id)

    def _resolve_athlete_name(self, session: Session, athlete_id: Optional[int]) -> str:
        """Resolve athlete name fallback-safe for scoreboard labels."""
        if athlete_id is None:
            return "ATLETA"
        athlete = session.get(Athlete, athlete_id)
        if athlete is None:
            return "ATLETA"
        return athlete.name

    def _build_penalty_slots(self, penalties: list[Penalty]) -> dict[str, bool]:
        """Build cumulative slot map for scoreboard from latest penalty level."""
        slots = {"C1": False, "C2": False, "C3": False, "HC": False, "H": False}
        if not penalties:
            return slots

        latest = penalties[-1].penalty_type
        if latest == "CHUI":
            chui_count = sum(
                1 for penalty in penalties if penalty.penalty_type == "CHUI"
            )
            slots["C1"] = True
            if chui_count >= 2:
                slots["C2"] = True
            if chui_count >= 3:
                slots["C3"] = True
            return slots
        if latest == "C1":
            slots["C1"] = True
            return slots
        if latest == "C2":
            slots["C1"] = True
            slots["C2"] = True
            return slots
        if latest == "C3":
            slots["C1"] = True
            slots["C2"] = True
            slots["C3"] = True
            return slots
        if latest == PenaltyType.HANSOKU_CHUI.value:
            slots["C1"] = True
            slots["C2"] = True
            slots["C3"] = True
            slots["HC"] = True
            return slots
        if latest == PenaltyType.HANSOKU.value:
            slots["C1"] = True
            slots["C2"] = True
            slots["C3"] = True
            slots["HC"] = True
            slots["H"] = True
            return slots
        return slots

    def _sync_from_match(self, session: Session, match_id: int) -> None:
        """Sync all public scoreboard vars from persisted match state."""
        match = session.get(Match, match_id)
        if match is None:
            self.match_id = 0
            self._reset_scoreboard(exhibition_mode=False)
            return

        self.match_id = match.id
        self.has_active_match = True
        self.is_exhibition_mode = False
        self.aka_score = match.aka_score
        self.ao_score = match.ao_score
        self.aka_name = self._resolve_athlete_name(
            session=session,
            athlete_id=match.aka_id,
        )
        self.ao_name = self._resolve_athlete_name(
            session=session,
            athlete_id=match.ao_id,
        )
        self.aka_senshu = match.aka_senshu
        self.ao_senshu = match.ao_senshu

        aka_penalties = session.exec(
            select(Penalty)
            .where(
                Penalty.match_id == match.id,
                Penalty.participant == Participant.AKA.value,
            )
            .order_by(Penalty.id.asc())
        ).all()
        ao_penalties = session.exec(
            select(Penalty)
            .where(
                Penalty.match_id == match.id,
                Penalty.participant == Participant.AO.value,
            )
            .order_by(Penalty.id.asc())
        ).all()
        self.aka_penalty_slots = self._build_penalty_slots(aka_penalties)
        self.ao_penalty_slots = self._build_penalty_slots(ao_penalties)

    def _guard_active_match_event(self) -> Any:
        """Return warning toast event when no active match exists."""
        if self.match_id <= 0:
            self.error_message = "No active match"
            return rx.toast.warning("No active match")
        return None

    def _guard_real_mode_or_exhibition_event(self) -> Any:
        """Allow action in exhibition; require match in real mode."""
        if self.is_exhibition_mode and self.match_id <= 0:
            return None
        return self._guard_active_match_event()

    def _resolve_match_duration(self, session: Session, match: Match) -> int:
        """Resolve match base duration from category definition."""
        category = session.get(TournamentCategory, match.category_id)
        if category is None:
            return 180
        return int(category.match_duration_seconds or 180)

    @rx.event
    async def enable_exhibition_mode(self) -> None:
        """Switch scoreboard to free exhibition mode without active match."""
        self.match_id = 0
        self._reset_scoreboard()

    @rx.event
    async def load_match(self) -> None:
        """Load match from route id and initialize timer by category duration."""
        self.error_message = ""
        self.timer_running = False
        self._timer_loop_active = False
        self.is_exhibition_mode = False
        try:
            match_id = self._parse_match_id()
        except ValueError:
            self.error_message = "ID de encuentro inválido"
            self.match_id = 0
            self._reset_scoreboard(exhibition_mode=False)
            return

        with rx.session() as session:
            match = session.get(Match, match_id)
            if match is None:
                self.error_message = "Encuentro no encontrado"
                self.match_id = 0
                self._reset_scoreboard(exhibition_mode=False)
                return

            self._sync_from_match(session=session, match_id=match_id)
            base_seconds = self._resolve_match_duration(session=session, match=match)

        self.timer_base_seconds = base_seconds
        self.timer_seconds = base_seconds
        self.timer_running = False
        self._timer_loop_active = False

    @rx.event
    async def start_timer(self) -> None:
        """Start live timer when mode permits."""
        warning_event = self._guard_real_mode_or_exhibition_event()
        if warning_event is not None:
            yield warning_event
            return
        if self.timer_seconds <= 0:
            return
        self.timer_running = True
        if not self._timer_loop_active:
            self._timer_loop_active = True
            yield KumiteMatchState.run_timer_loop

    @rx.event
    async def stop_timer(self) -> None:
        """Stop timer without changing value."""
        self.timer_running = False
        self._timer_loop_active = False

    @rx.event
    async def reset_timer(self) -> None:
        """Reset timer to category/exhibition base value."""
        warning_event = self._guard_real_mode_or_exhibition_event()
        if warning_event is not None:
            yield warning_event
            return
        self.timer_running = False
        self._timer_loop_active = False
        self.timer_seconds = self.timer_base_seconds

    @rx.event
    async def set_timer(self, seconds: int) -> None:
        """Set timer base/seconds manually and stop timer."""
        warning_event = self._guard_real_mode_or_exhibition_event()
        if warning_event is not None:
            yield warning_event
            return
        next_seconds = max(int(seconds), 0)
        self.timer_running = False
        self._timer_loop_active = False
        self.timer_base_seconds = next_seconds
        self.timer_seconds = next_seconds

    @rx.event
    async def add_or_substract_timer(self, seconds: int) -> None:
        """Adjust current timer by ± seconds and stop timer."""
        warning_event = self._guard_real_mode_or_exhibition_event()
        if warning_event is not None:
            yield warning_event
            return
        self.timer_running = False
        self._timer_loop_active = False
        self.timer_seconds = max(self.timer_seconds + int(seconds), 0)

    @rx.event(background=True)
    async def run_timer_loop(self) -> None:
        """Drive countdown in background while timer_running is true."""
        while True:
            await asyncio.sleep(1)

            toast_event = None
            async with self:
                if not self.timer_running:
                    self._timer_loop_active = False
                    break

                if self.timer_seconds <= 0:
                    self.timer_seconds = 0
                    self.timer_running = False
                    self._timer_loop_active = False
                    break

                self.timer_seconds -= 1
                if self.timer_seconds <= 0:
                    self.timer_seconds = 0
                    self.timer_running = False
                    self._timer_loop_active = False
                    toast_event = rx.toast.success("¡Combate terminado!")

            if toast_event is not None:
                yield toast_event
                break

    @rx.event
    async def tick_timer(self) -> None:
        """Advance one second in running timer and emit end signal."""
        if not self.timer_running:
            return
        if self.timer_seconds <= 0:
            self.timer_running = False
            return

        self.timer_seconds -= 1
        if self.timer_seconds <= 0:
            self.timer_seconds = 0
            self.timer_running = False
            yield rx.toast.success("¡Combate terminado!")

    def _is_latest_action_shikkaku(self, session: Session) -> bool:
        """Detect whether latest action corresponds to SHIKKAKU penalty."""
        action_log = session.exec(
            select(MatchActionLog)
            .where(MatchActionLog.match_id == self.match_id)
            .order_by(MatchActionLog.id.desc())
        ).first()
        if action_log is None or action_log.action_kind != "PENALTY_APPLY":
            return False
        try:
            payload = json.loads(action_log.before_snapshot)
        except json.JSONDecodeError:
            return False
        created_penalty_ids = payload.get("created_penalty_ids", [])
        if not created_penalty_ids:
            return False
        penalty = session.get(Penalty, int(created_penalty_ids[-1]))
        return (
            penalty is not None
            and penalty.penalty_type == PenaltyType.SHIKKAKU.value
        )

    def _update_last_penalty_display(self, participant: str, penalty_type: str) -> None:
        """Update frontend display string for last applied penalty.

        Args:
            participant: Match side receiving the penalty (AKA/AO).
            penalty_type: Penalty type string to display.
        """
        if participant == "AKA":
            self.last_penalty_aka = penalty_type
        elif participant == "AO":
            self.last_penalty_ao = penalty_type

    async def _call_with_pause(self, fn: Callable[[], None]) -> tuple[bool, str]:
        """Execute backend operation with timer pause/resume and error handling.

        Args:
            fn: Zero-argument callable running backend operation.

        Returns:
            Tuple of operation status and error message.
        """
        self.timer_paused = True
        self.error_message = ""
        self._processing = True
        try:
            fn()
            return True, ""
        except (
            AthleteSchedulingConflictError,
            PenaltyRemovalNotAllowedError,
            PenaltyEscalationError,
            ValueError,
        ) as error:
            self.error_message = str(error)
            return False, self.error_message
        finally:
            self.timer_paused = False
            self._processing = False

    @rx.event
    async def apply_penalty_cumulative(self, participant: str) -> None:
        """Apply next penalty in escalation cycle.

        Args:
            participant: Side receiving penalty (AKA/AO).
        """

        if self.is_exhibition_mode and self.match_id <= 0:
            self._apply_exhibition_penalty(participant=participant)
            return

        warning_event = self._guard_active_match_event()
        if warning_event is not None:
            yield warning_event
            return

        success, message = await self._call_with_pause(
            lambda: self._apply_penalty(participant=participant, penalty_type=None)
        )
        if not success:
            yield rx.toast.error(message)

    @rx.event
    async def apply_penalty_direct(self, participant: str, penalty_type: str) -> None:
        """Apply explicit penalty type selected by operator.

        Args:
            participant: Side receiving penalty (AKA/AO).
            penalty_type: Explicit penalty enum name/value string.
        """
        warning_event = self._guard_active_match_event()
        if warning_event is not None:
            yield warning_event
            return

        success, message = await self._call_with_pause(
            lambda: self._apply_penalty(
                participant=participant,
                penalty_type=PenaltyType(penalty_type),
            )
        )
        if not success:
            yield rx.toast.error(message)

    @rx.event
    async def remove_last_penalty(self, participant: str) -> None:
        """Remove the most recent penalty for one participant.

        Args:
            participant: Side from which last penalty is removed (AKA/AO).
        """

        warning_event = self._guard_active_match_event()
        if warning_event is not None:
            yield warning_event
            return

        success, message = await self._call_with_pause(
            lambda: self._remove_last_penalty(participant=participant)
        )
        if not success:
            yield rx.toast.error(message)

    @rx.event
    async def apply_score(
        self,
        participant: str,
        score_type: str,
        applied_by_id: int = 1,
    ) -> None:
        """Apply score using service and refresh state from DB."""
        if self.is_exhibition_mode and self.match_id <= 0:
            self._apply_exhibition_score(
                participant=participant,
                score_type=score_type,
            )
            return

        warning_event = self._guard_active_match_event()
        if warning_event is not None:
            yield warning_event
            return

        self.timer_paused = True
        self.error_message = ""
        self._processing = True
        try:
            result = KumiteScoringService.apply_score(
                match_id=self.match_id,
                participant=participant,
                score_type=score_type,
                applied_by_id=applied_by_id,
            )
            if not result.success:
                self.error_message = result.message
                yield rx.toast.error(result.message)
                return
            with rx.session() as session:
                self._sync_from_match(session=session, match_id=self.match_id)
            self.last_action_label = f"SCORE:{participant}:{score_type}"
        finally:
            self.timer_paused = False
            self._processing = False

    @rx.event
    async def undo_last_action(self) -> None:
        """Undo latest action through persisted service path."""
        if self.is_exhibition_mode and self.match_id <= 0:
            self._undo_exhibition_action()
            return

        warning_event = self._guard_active_match_event()
        if warning_event is not None:
            yield warning_event
            return

        self.timer_paused = True
        self.error_message = ""
        self._processing = True
        try:
            with rx.session() as session:
                if self._is_latest_action_shikkaku(session=session):
                    message = "SHIKKAKU undo blocked. Use admin revert flow."
                    self.error_message = message
                    yield rx.toast.error(message)
                    return

            result = KumiteScoringService.undo_last_action(self.match_id)
            if not result.success:
                self.error_message = result.message
                yield rx.toast.error(result.message)
                return

            with rx.session() as session:
                self._sync_from_match(session=session, match_id=self.match_id)
            self.last_action_label = "UNDO"
        finally:
            self.timer_paused = False
            self._processing = False

    @rx.event
    async def apply_manual_senshu(self, participant: str) -> None:
        """Apply manual senshu in exhibition or persisted real match."""
        if self.is_exhibition_mode and self.match_id <= 0:
            self._apply_exhibition_manual_senshu(participant=participant)
            return

        warning_event = self._guard_active_match_event()
        if warning_event is not None:
            yield warning_event
            return

        self.error_message = ""
        result = KumiteScoringService.apply_manual_senshu(
            self.match_id,
            participant,
        )
        if not result.success:
            self.error_message = result.message
            yield rx.toast.error(result.message)
            return

        with rx.session() as session:
            self._sync_from_match(session=session, match_id=self.match_id)
        self.last_action_label = f"SENSHU-SET:{participant}"

    @rx.event
    async def revoke_manual_senshu(self, participant: str) -> None:
        """Revoke manual senshu in exhibition or persisted real match."""
        if self.is_exhibition_mode and self.match_id <= 0:
            self._revoke_exhibition_manual_senshu(participant=participant)
            return

        warning_event = self._guard_active_match_event()
        if warning_event is not None:
            yield warning_event
            return

        self.error_message = ""
        result = KumiteScoringService.revoke_senshu(self.match_id, participant)
        if not result.success:
            self.error_message = result.message
            yield rx.toast.error(result.message)
            return

        with rx.session() as session:
            self._sync_from_match(session=session, match_id=self.match_id)
        self.last_action_label = f"SENSHU-REVOKE:{participant}"

    def _apply_penalty(
        self,
        participant: str,
        penalty_type: Optional[PenaltyType],
    ) -> None:
        """Execute backend service call and sync display state.

        Args:
            participant: Side receiving penalty.
            penalty_type: Optional explicit penalty type.
        """
        with rx.session() as session:
            penalty = kumite_scoring_service.apply_penalty(
                session=session,
                match_id=self.match_id,
                participant=participant,
                penalty_type=penalty_type,
            )
            self._sync_from_match(session=session, match_id=self.match_id)
        self._update_last_penalty_display(participant, penalty.penalty_type)

    def _remove_last_penalty(self, participant: str) -> None:
        """Execute backend removal and clear side display if needed.

        Args:
            participant: Side to remove from.
        """
        with rx.session() as session:
            kumite_scoring_service.remove_last_penalty(
                session=session,
                match_id=self.match_id,
                participant=participant,
            )
            self._sync_from_match(session=session, match_id=self.match_id)
        self._update_last_penalty_display(participant, "")
