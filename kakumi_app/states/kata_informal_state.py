"""Reflex state for informal Kata table-first operator flow."""

from __future__ import annotations

from typing import Any

import reflex as rx
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.services.kata_informal_service import KataInformalService


class KataInformalState(rx.State):
    """Dedicated state for informal Kata scoring and finalization."""

    category_id: int = 0
    roster: list[dict[str, object]] = []
    standings: list[dict[str, object]] = []
    selected_athlete_id: int = 0
    judge_entries: dict[str, str] = {
        "J1": "",
        "J2": "",
        "J3": "",
        "J4": "",
        "J5": "",
    }
    error_message: str = ""

    @rx.var
    def current_athlete_label(self) -> str:
        """Return label for currently active athlete."""
        if self.selected_athlete_id <= 0:
            return ""
        for row in self.roster:
            if int(row.get("id", 0)) == self.selected_athlete_id:
                return f"{int(row['id'])} - {str(row['name'])}"
        return ""

    @rx.var
    def can_finalize_performance(self) -> bool:
        """Return true when selected athlete and complete panel exist."""
        if self.selected_athlete_id <= 0:
            return False
        return all(
            self.judge_entries.get(slot, "") != ""
            for slot in ("J1", "J2", "J3", "J4", "J5")
        )

    @rx.var
    def roster_labels(self) -> list[str]:
        """Return select labels with embedded athlete id."""
        return [
            f"{int(row['id'])} - {str(row['name'])}"
            for row in self.roster
            if "id" in row and "name" in row
        ]

    def _route_params(self) -> dict[str, Any]:
        """Safely read route params."""
        try:
            return dict(self.router.page.params)
        except Exception:
            page = getattr(self.router, "_page", None)
            return dict(getattr(page, "params", {}) or {})

    def _parse_category_id(self) -> int:
        """Parse category id from route."""
        params = self._route_params()
        raw_id = params.get("category_id", params.get("id"))
        if raw_id in (None, ""):
            raise ValueError("ID de categoría inválido")
        return int(raw_id)

    def _build_standings(self) -> list[dict[str, object]]:
        """Build render-ready standings with rank and athlete labels."""
        ranking = KataInformalService.rank_category(self.category_id)
        roster_name_map = {
            int(row["id"]): str(row["name"])
            for row in self.roster
            if "id" in row and "name" in row
        }
        return [
            {
                "rank": index + 1,
                "athlete_id": int(row["athlete_id"]),
                "athlete_name": roster_name_map.get(int(row["athlete_id"]), "—"),
                "final_score": f"{float(row['final_score']):.3f}",
                "victory_points": int(row.get("victory_points", 0)),
                "needs_extra_kata": bool(row["needs_extra_kata"]),
            }
            for index, row in enumerate(ranking)
        ]

    def _advance_to_next_athlete(self) -> None:
        """Move active athlete to next roster entry in sequence."""
        if not self.roster:
            self.selected_athlete_id = 0
            return

        roster_ids = [int(row["id"]) for row in self.roster if "id" in row]
        if not roster_ids:
            self.selected_athlete_id = 0
            return

        if self.selected_athlete_id not in roster_ids:
            self.selected_athlete_id = roster_ids[0]
            return

        current_index = roster_ids.index(self.selected_athlete_id)
        next_index = (current_index + 1) % len(roster_ids)
        self.selected_athlete_id = roster_ids[next_index]

    @rx.event
    async def load_category_session(self) -> None:
        """Load informal roster and current standings."""
        self.error_message = ""
        try:
            self.category_id = self._parse_category_id()
        except ValueError:
            self.error_message = "ID de categoría inválido"
            return

        with rx.session() as session:
            athletes = session.exec(
                select(Athlete)
                .where(Athlete.kata_category_id == self.category_id)
                .order_by(Athlete.name)
            ).all()

        self.roster = [{"id": athlete.id, "name": athlete.name} for athlete in athletes]
        self.standings = self._build_standings()
        self.selected_athlete_id = (
            int(self.roster[0]["id"]) if len(self.roster) > 0 else 0
        )
        self.judge_entries = {"J1": "", "J2": "", "J3": "", "J4": "", "J5": ""}

    @rx.event
    async def select_athlete(self, athlete_id: str) -> None:
        """Select athlete for next run."""
        self.selected_athlete_id = int(athlete_id)
        self.judge_entries = {"J1": "", "J2": "", "J3": "", "J4": "", "J5": ""}
        self.error_message = ""

    @rx.event
    async def select_athlete_from_label(self, label: str) -> None:
        """Parse id from select label and forward to selector."""
        athlete_id = str(label).split(" - ")[0]
        await self.select_athlete(athlete_id)

    @rx.event
    async def set_judge_score(self, judge_slot: str, value: str) -> None:
        """Set one judge input in panel."""
        if judge_slot not in self.judge_entries:
            return
        updated = dict(self.judge_entries)
        updated[judge_slot] = value.strip()
        self.judge_entries = updated

    @rx.event
    async def finalize_performance(self):
        """Persist one athlete run and refresh ranking table."""
        self.error_message = ""
        if self.selected_athlete_id <= 0:
            self.error_message = "Seleccioná un atleta"
            return

        values: list[float] = []
        for slot in ("J1", "J2", "J3", "J4", "J5"):
            raw = self.judge_entries.get(slot, "")
            if raw == "":
                self.error_message = "Panel incompleto"
                return
            values.append(float(raw))

        KataInformalService.save_performance(
            category_id=self.category_id,
            athlete_id=self.selected_athlete_id,
            judge_scores=values,
        )
        self.standings = self._build_standings()
        self.judge_entries = {"J1": "", "J2": "", "J3": "", "J4": "", "J5": ""}
        self._advance_to_next_athlete()

    @rx.event
    async def finalize_category(self):
        """Close informal category and assign podium."""
        self.error_message = ""
        try:
            KataInformalService.finalize_category(self.category_id)
        except ValueError as error:
            self.error_message = str(error)
