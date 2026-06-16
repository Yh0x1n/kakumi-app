"""
Team State
Manages CRUD operations for teams.
"""

from typing import Any, Optional

import reflex as rx
from sqlmodel import select

from kakumi_app.models.team_model import Team
from kakumi_app.models.tournament_model import TournamentCategory


class TeamState(rx.State):
    """State for team management."""

    # Shared CRUD UI vars (mirrored for Reflex state registration)
    is_editing: bool = False
    show_form: bool = False
    error_message: str = ""
    search_query: str = ""
    current_page: int = 1
    page_size: int = 10
    search_query: str = ""

    teams: list[dict[str, Any]] = []
    current_team: Optional[dict[str, Any]] = None
    categories: list[dict[str, Any]] = []

    # Form fields
    name: str = ""
    dojo: str = ""
    category_id: str = ""  # string for select
    is_active: bool = True


    def _set_form_open(self, editing: bool) -> None:
        """Open form with desired mode and clean inline errors."""
        self.is_editing = editing
        self.show_form = True
        self.error_message = ""

    def apply_search_query(self, value: str) -> None:
        """Normalize search value and reset pagination cursor."""
        self.search_query = value.strip()
        self.current_page = 1

    def paginate_rows(self, rows: list[dict]) -> list[dict]:
        """Return a deterministic page slice for in-memory rows."""
        if self.page_size <= 0:
            return rows
        start = max(self.current_page - 1, 0) * self.page_size
        end = start + self.page_size
        return rows[start:end]

    def reset_filters(self) -> None:
        """Reset default filter controls used by CRUD pages."""
        self.search_query = ""
        self.current_page = 1
    @rx.var
    def category_options(self) -> list[str]:
        """Category labels for team form select."""
        return [f"{cat['id']}: {cat['name']}" for cat in self.categories]

    @rx.event
    async def load_teams(self) -> None:
        """Load all teams from database."""
        with rx.session() as session:
            teams = session.exec(select(Team)).all()
            categories = session.exec(select(TournamentCategory)).all()
            self.teams = [team.model_dump(mode="json") for team in teams]
            self.categories = [
                category.model_dump(mode="json") for category in categories
            ]

    @rx.event
    async def filter_teams(self) -> None:
        """Filter teams by search query."""
        if not self.search_query:
            await self.load_teams()
            return

        query = self.search_query.lower()
        with rx.session() as session:
            all_teams = session.exec(select(Team)).all()
            self.teams = [
                t.model_dump(mode="json")
                for t in all_teams
                if query in t.name.lower() or (t.dojo and query in t.dojo.lower())
            ]

    @rx.event
    def set_form_values(
        self,
        _: Any,
        team: Optional[dict[str, Any]] = None,
    ) -> None:
        """Set form values for editing or creating."""
        if team:
            self.current_team = team
            self._set_form_open(editing=True)
            self.name = team.get("name", "")
            self.dojo = team.get("dojo") or ""
            self.category_id = str(team.get("category_id", ""))
            self.is_active = bool(team.get("is_active", True))
        else:
            self.current_team = None
            self._set_form_open(editing=False)
            self.reset_form()

    def reset_form(self) -> None:
        """Reset form fields."""
        self.name = ""
        self.dojo = ""
        self.category_id = ""
        self.is_active = True

    def validate_form(self) -> bool:
        """Validate form fields."""
        if not self.name or len(self.name) < 2 or len(self.name) > 255:
            self.error_message = "Name must be 2-255 characters"
            return False

        if not self.category_id:
            self.error_message = "Category is required"
            return False

        try:
            cat_id = int(self.category_id)
            with rx.session() as session:
                category = session.get(TournamentCategory, cat_id)
                if not category:
                    self.error_message = "Category not found"
                    return False
        except ValueError:
            self.error_message = "Invalid category ID"
            return False

        return True

    @rx.event
    async def save_team(self) -> Any:
        """Save team (create or update)."""
        if not self.validate_form():
            return

        self.error_message = ""

        category_id = int(self.category_id)

        team_data = {
            "name": self.name,
            "dojo": self.dojo or None,
            "category_id": category_id,
            "member_count": 0,  # Will be updated when members added
            "is_active": self.is_active,
        }

        with rx.session() as session:
            if self.is_editing and self.current_team:
                # Update existing
                team_id = self.current_team.get("id")
                team = session.get(Team, int(team_id)) if team_id else None
                if not team:
                    return rx.toast.error("Team not found")

                for key, value in team_data.items():
                    setattr(team, key, value)

                session.add(team)
                session.commit()
                success_message = f"Team '{team.name}' updated successfully"
            else:
                # Check duplicate name
                existing = session.exec(
                    select(Team).where(Team.name == self.name)
                ).first()
                if existing:
                    return rx.toast.error(
                        f"Team with name '{self.name}' already exists"
                    )

                team = Team(**team_data)
                session.add(team)
                session.commit()
                success_message = f"Team '{team.name}' created successfully"

        self.show_form = False
        await self.load_teams()
        return rx.toast.success(success_message)

    @rx.event
    async def delete_team(self, team_id: int) -> Any:
        """Delete team by ID."""
        with rx.session() as session:
            team = session.get(Team, team_id)
            if not team:
                return rx.toast.error("Team not found")

            team_name = team.name
            session.delete(team)
            session.commit()

        await self.load_teams()
        return rx.toast.success(f"Team '{team_name}' deleted")

    @rx.event
    def cancel_form(self) -> None:
        """Cancel form and hide it using shared mixin logic."""
        self.show_form = False
        self.error_message = ""

    @rx.event
    def initialize_new_team_form(self) -> None:
        """Prepare clean form state when opening new team route."""
        self.set_form_values(None)
