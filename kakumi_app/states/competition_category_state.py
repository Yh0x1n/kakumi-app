"""State for operator category competition visibility."""

from __future__ import annotations

import logging
from typing import Any

import reflex as rx
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete, AthleteGender
from kakumi_app.models.referee_model import Referee
from kakumi_app.models.team_model import Team
from kakumi_app.models.tournament_model import (
    CategoryGender,
    Match,
    Tatami,
    TournamentCategory,
)
from kakumi_app.services.kata_informal_service import KataInformalService
from kakumi_app.states.kata_informal_state import KataInformalState
from kakumi_app.utils import (
    BELT_RANKS,
    BELT_RANK_ORDER,
    CompetitionCategoryData,
    MatchCardData,
    build_match_cards,
)


logger = logging.getLogger(__name__)


class CompetitionCategoryState(rx.State):
    """Load category and match list data for operator views."""

    category: CompetitionCategoryData | dict[str, Any] = {}
    matches: list[MatchCardData] = []
    is_loading: bool = False
    error_message: str = ""
    informal_standings: list[dict[str, Any]] = []
    is_informal_mode: bool = False

    def _route_params(self) -> dict[str, Any]:
        """Safely resolve route params from the router state."""
        try:
            return dict(self.router.page.params)
        except Exception:
            page = getattr(self.router, "_page", None)
            return dict(getattr(page, "params", {}) or {})

    def _parse_category_id(self) -> int:
        """Parse the category id route param or raise ValueError."""
        params = self._route_params()
        raw_category_id = params.get("category_id", params.get("id"))
        if raw_category_id in (None, ""):
            raise ValueError("ID de categoría inválido")
        return int(raw_category_id)

    @staticmethod
    def _name_lookup(session: Any, model: Any, ids: set[int]) -> dict[int, str]:
        """Fetch an id-to-name mapping for a given model."""
        if not ids:
            return {}

        rows = session.exec(
            select(model.id, model.name).where(model.id.in_(sorted(ids)))
        ).all()
        return {row[0]: row[1] for row in rows}

    @rx.event
    async def load_category(self) -> None:
        """Load operator-facing category match data for the current route."""
        self.is_loading = True
        self.error_message = ""
        self.category = {}
        self.matches = []
        self.informal_standings = []
        self.is_informal_mode = False

        try:
            category_id = self._parse_category_id()

            with rx.session() as session:
                category = session.get(TournamentCategory, category_id)
                if category is None:
                    self.category = {}
                    self.error_message = "Categoría no encontrada"
                    return

                matches = session.exec(
                    select(Match)
                    .where(Match.category_id == category_id)
                    .order_by(Match.round, Match.position, Match.id)
                ).all()

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
                    match.tatami_id for match in matches if match.tatami_id is not None
                }
                referee_ids = {
                    match.referee_id
                    for match in matches
                    if match.referee_id is not None
                }
                matched_query = select(Athlete).where(
                    Athlete.age.between(category.min_age, category.max_age)
                )
                if category.gender == CategoryGender.MALE.value:
                    matched_query = matched_query.where(
                        Athlete.gender == AthleteGender.MALE.value
                    )
                elif category.gender == CategoryGender.FEMALE.value:
                    matched_query = matched_query.where(
                        Athlete.gender == AthleteGender.FEMALE.value
                    )

                matched_roster = session.exec(matched_query).all()

                if category.min_belt_rank or category.max_belt_rank:
                    min_idx = BELT_RANK_ORDER.get(category.min_belt_rank, 0)
                    max_idx = BELT_RANK_ORDER.get(
                        category.max_belt_rank, len(BELT_RANKS) - 1
                    )
                    matched_roster = [
                        a
                        for a in matched_roster
                        if a.belt_rank
                        and min_idx
                        <= BELT_RANK_ORDER.get(a.belt_rank, -1)
                        <= max_idx
                    ]

                roster_athlete_ids = {a.id for a in matched_roster}

                athlete_names = self._name_lookup(
                    session,
                    Athlete,
                    athlete_ids | roster_athlete_ids,
                )
                team_names = self._name_lookup(session, Team, team_ids)
                tatami_names = self._name_lookup(session, Tatami, tatami_ids)
                referee_names = self._name_lookup(session, Referee, referee_ids)

                kata_flow_mode = str(getattr(category, "kata_flow_mode", "STANDARD"))

            self.category = {
                "id": category.id,
                "name": category.name,
                "modality": category.modality,
                "competition_system": category.competition_system,
                "status": category.status,
                "kata_flow_mode": kata_flow_mode,
            }
            if kata_flow_mode == "INFORMAL":
                self.is_informal_mode = True
                standings = KataInformalService.rank_category(category.id)
                self.informal_standings = [
                    {
                        "rank": index + 1,
                        "athlete_id": row["athlete_id"],
                        "athlete_name": athlete_names.get(int(row["athlete_id"]), "—"),
                        "final_score": f"{float(row['final_score']):.3f}",
                        "needs_extra_kata": row["needs_extra_kata"],
                    }
                    for index, row in enumerate(standings)
                ]
                self.matches = []
                return KataInformalState.load_category_session
            else:
                self.matches = build_match_cards(
                    matches,
                    athlete_names=athlete_names,
                    team_names=team_names,
                    tatami_names=tatami_names,
                    referee_names=referee_names,
                    category_modalities={category.id: str(category.modality)},
                )
        except ValueError:
            self.category = {}
            self.error_message = "ID de categoría inválido"
        except Exception:
            self.category = {}
            logger.exception("Error cargando categoría de competencia")
            self.error_message = "Error cargando datos"
        finally:
            self.is_loading = False

    @rx.event
    async def set_kata_flow_mode(self, mode: str) -> None:
        """Persist kata flow mode for current category."""
        if mode not in {"STANDARD", "INFORMAL"}:
            return
        try:
            category_id = self._parse_category_id()
        except ValueError:
            self.error_message = "ID de categoría inválido"
            return

        with rx.session() as session:
            category = session.get(TournamentCategory, category_id)
            if category is None:
                self.error_message = "Categoría no encontrada"
                return
            category.kata_flow_mode = mode
            session.add(category)
            session.commit()

        await self.load_category()
