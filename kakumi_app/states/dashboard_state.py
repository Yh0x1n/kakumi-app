"""Reflex state for the authenticated dashboard (route /home)."""

from __future__ import annotations

import logging
from typing import Any

import reflex as rx

from kakumi_app.services.results_service import ResultsService
from kakumi_app.states.auth_state import AuthState

logger = logging.getLogger(__name__)


class DashboardState(rx.State):
    """State container for the authenticated dashboard (route /home)."""

    winner_cards: list[dict[str, Any]] = []
    is_loading: bool = False

    @rx.event
    async def load_recent_winners(self) -> None:
        """Fetch up to 4 recent winner cards from results service."""
        auth = await self.get_state(AuthState)
        if not auth.is_authenticated:
            return
        self.is_loading = True
        try:
            self.winner_cards = ResultsService.get_recent_winners()
        except Exception:
            logger.exception("Error loading recent winners")
            self.winner_cards = []
        finally:
            self.is_loading = False
