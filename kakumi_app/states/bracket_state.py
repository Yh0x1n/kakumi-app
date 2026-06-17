"""State for tournament bracket visibility pages."""

from __future__ import annotations

import logging
from typing import Any

import reflex as rx
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.referee_model import Referee
from kakumi_app.models.team_model import Team
from kakumi_app.models.tournament_model import (
    Match,
    Tatami,
    Tournament,
    TournamentCategory,
)
from kakumi_app.services.kata_informal_service import KataInformalService
from kakumi_app.utils import (
    BracketCategoryData,
    TournamentBracketData,
    build_match_cards,
    group_matches_by_round,
)


logger = logging.getLogger(__name__)


class BracketState(rx.State):
    """Load tournament bracket data into JSON-serializable state vars."""

    tournament: TournamentBracketData | dict[str, Any] = {}
    categories: list[BracketCategoryData] = []
    is_loading: bool = False
    error_message: str = ""

    def _route_params(self) -> dict[str, Any]:
        """Safely resolve route params from the router state."""
        try:
            return dict(self.router.page.params)
        except Exception:
            page = getattr(self.router, "_page", None)
            return dict(getattr(page, "params", {}) or {})

    def _parse_tournament_id(self) -> int:
        """Parse the tournament id route param or raise ValueError."""
        raw_tournament_id = self._route_params().get("id")
        if raw_tournament_id in (None, ""):
            raise ValueError("ID de torneo inválido")
        return int(raw_tournament_id)

    @staticmethod
    def _name_lookup(session: Any, model: Any, ids: set[int]) -> dict[int, str]:
        """Fetch an id-to-name mapping for a given model."""
        if not ids:
            return {}

        rows = session.exec(
            select(model.id, model.name).where(model.id.in_(sorted(ids)))
        ).all()
        return {row[0]: row[1] for row in rows}

    @staticmethod
    def _build_informal_standings(category_id: int) -> list[dict[str, object]]:
        """Build standings payload for an INFORMAL kata category."""
        ranking = KataInformalService.rank_category(category_id)
        if not ranking:
            return []

        athlete_ids = {
            int(row["athlete_id"])
            for row in ranking
            if row.get("athlete_id") is not None
        }
        with rx.session() as session:
            rows = session.exec(
                select(Athlete.id, Athlete.name).where(
                    Athlete.id.in_(sorted(athlete_ids))
                )
            ).all() if athlete_ids else []
        name_by_id: dict[int, str] = {row[0]: row[1] for row in rows}

        return [
            {
                "rank": index + 1,
                "athlete_id": int(row["athlete_id"]),
                "athlete_name": name_by_id.get(
                    int(row["athlete_id"]), "—"
                ),
                "final_score": f"{float(row['final_score']):.3f}",
                "needs_extra_kata": bool(row.get("needs_extra_kata", False)),
            }
            for index, row in enumerate(ranking)
        ]

    @rx.event
    async def load_bracket(self) -> None:
        """Load bracket data for the current tournament route."""
        self.is_loading = True
        self.error_message = ""
        self.tournament = {}
        self.categories = []

        try:
            tournament_id = self._parse_tournament_id()

            with rx.session() as session:
                tournament = session.get(Tournament, tournament_id)
                if tournament is None:
                    self.error_message = "Torneo no encontrado"
                    return

                categories = session.exec(
                    select(TournamentCategory)
                    .where(TournamentCategory.tournament_id == tournament_id)
                    .order_by(TournamentCategory.id)
                ).all()

                category_ids = [category.id for category in categories]
                matches = (
                    session.exec(
                        select(Match)
                        .where(Match.category_id.in_(category_ids))
                        .order_by(
                            Match.category_id,
                            Match.round,
                            Match.position,
                            Match.id,
                        )
                    ).all()
                    if category_ids
                    else []
                )

                athlete_ids = {
                    participant_id
                    for match in matches
                    for participant_id in (match.aka_id, match.ao_id)
                    if participant_id is not None
                }
                team_ids = {
                    participant_id
                    for match in matches
                    for participant_id in (match.aka_team_id, match.ao_team_id)
                    if participant_id is not None
                }
                tatami_ids = {
                    match.tatami_id
                    for match in matches
                    if match.tatami_id is not None
                }
                referee_ids = {
                    match.referee_id
                    for match in matches
                    if match.referee_id is not None
                }

                athlete_names = self._name_lookup(session, Athlete, athlete_ids)
                team_names = self._name_lookup(session, Team, team_ids)
                tatami_names = self._name_lookup(session, Tatami, tatami_ids)
                referee_names = self._name_lookup(session, Referee, referee_ids)

            matches_by_category: dict[int, list[Match]] = {}
            for match in matches:
                matches_by_category.setdefault(match.category_id, []).append(match)

            self.tournament = {
                "id": tournament.id,
                "name": tournament.name,
                "status": tournament.status,
                "tatami_count": tournament.tatami_count,
            }
            self.categories = [
                {
                    "id": category.id,
                    "name": category.name,
                    "modality": category.modality,
                    "competition_system": category.competition_system,
                    "status": category.status,
                    "kata_flow_mode": getattr(
                        category, "kata_flow_mode", "STANDARD"
                    ),
                    "standings": [],
                    "rounds": group_matches_by_round(
                        build_match_cards(
                            matches_by_category.get(category.id, []),
                            athlete_names=athlete_names,
                            team_names=team_names,
                            tatami_names=tatami_names,
                            referee_names=referee_names,
                            category_modalities={
                                item.id: str(item.modality) for item in categories
                            },
                        )
                    ),
                }
                for category in categories
            ]

            for cat_data in self.categories:
                if cat_data["kata_flow_mode"] == "INFORMAL":
                    cat_data["standings"] = self._build_informal_standings(
                        cat_data["id"]
                    )
        except ValueError:
            self.error_message = "ID de torneo inválido"
        except Exception:
            logger.exception("Error cargando bracket del torneo")
            self.error_message = "Error cargando datos"
        finally:
            self.is_loading = False
