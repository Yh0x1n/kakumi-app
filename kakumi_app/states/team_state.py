"""
Team State
Manages CRUD operations for teams.
"""

from typing import List, Optional, Any

import reflex as rx
from sqlmodel import select

from kakumi_app.models.team_model import Team
from kakumi_app.models.tournament_model import TournamentCategory
from kakumi_app.states.base_crud_state import CrudStateMixin


class TeamState(CrudStateMixin, rx.State):
    """State for team management."""

    # Shared CRUD UI vars (mirrored for Reflex state registration)
    is_editing: bool = CrudStateMixin.is_editing
    show_form: bool = CrudStateMixin.show_form
    error_message: str = CrudStateMixin.error_message
    search_query: str = CrudStateMixin.search_query

    teams: List[Team] = []
    current_team: Optional[Team] = None
    categories: List[TournamentCategory] = []

    # Form fields
    name: str = ""
    dojo: str = ""
    category_id: str = ""  # string for select
    is_active: bool = True

    @rx.var
    def category_options(self) -> list[str]:
        """Category labels for team form select."""
        return [f"{cat.id}: {cat.name}" for cat in self.categories]

    @rx.event
    async def load_teams(self) -> None:
        """Load all teams from database."""
        with rx.session() as session:
            self.teams = session.exec(select(Team)).all()
            self.categories = session.exec(select(TournamentCategory)).all()

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
                t
                for t in all_teams
                if query in t.name.lower() or (t.dojo and query in t.dojo.lower())
            ]

    @rx.event
    def set_form_values(self, _: Any, team: Optional[Team] = None) -> None:
        """Set form values for editing or creating."""
        if team:
            self.current_team = team
            self._set_form_open(editing=True)
            self.name = team.name
            self.dojo = team.dojo or ""
            self.category_id = str(team.category_id)
            self.is_active = team.is_active
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
                team = session.get(Team, self.current_team.id)
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
        CrudStateMixin.cancel_form(self)

    @rx.event
    def initialize_new_team_form(self) -> None:
        """Prepare clean form state when opening new team route."""
        self.set_form_values(None)
