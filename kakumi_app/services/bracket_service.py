"""Bracket generation guard service."""

from typing import Any

import reflex as rx
from sqlmodel import Session, select

from kakumi_app.models.tournament_model import Match
from kakumi_app.services.tournament_service import ValidationError


BRACKET_ALREADY_EXISTS_MESSAGE = (
    "Bracket already generated for this category. Cannot regenerate."
)


class BracketService:
    """Minimal bracket service with regeneration guard."""

    def __init__(
        self,
        tournament_id: int,
        category_id: int,
        session: Session | None = None,
    ) -> None:
        self.tournament_id = tournament_id
        self.category_id = category_id
        self._session = session
        self._managed_session = session is None

    def _check_existing_matches(self) -> bool:
        if self._session is not None:
            return self._session.exec(self._existing_match_query()).first() is not None

        with rx.session() as session:
            return session.exec(self._existing_match_query()).first() is not None

    def _existing_match_query(self) -> Any:
        return select(Match).where(
            Match.tournament_id == self.tournament_id,
            Match.category_id == self.category_id,
        )

    def generate_bracket(self) -> dict[str, int | str]:
        """Return placeholder payload until real algorithm is implemented."""
        if self._check_existing_matches():
            raise ValidationError(
                code="BRACKET_ALREADY_EXISTS",
                message=BRACKET_ALREADY_EXISTS_MESSAGE,
            )

        return {
            "tournament_id": self.tournament_id,
            "category_id": self.category_id,
            "status": "ready",
        }
