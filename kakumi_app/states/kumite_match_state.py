"""Reflex state for managing a Kumite match in progress.

Handles timer pause/resume around penalty operations and
syncs with the backend scoring service.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Optional

import reflex as rx

from kakumi_app.models.tournament_model import PenaltyType
from kakumi_app.services import kumite_scoring_service
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
    timer_paused: bool = False
    error_message: str = ""
    last_penalty_aka: str = ""
    last_penalty_ao: str = ""

    # Backend-only vars
    _processing: bool = False

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

        success, message = await self._call_with_pause(
            lambda: self._remove_last_penalty(participant=participant)
        )
        if not success:
            yield rx.toast.error(message)

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
        self._update_last_penalty_display(participant, "")
