"""
Team State
Manages CRUD operations for teams.
"""

from typing import List, Optional, Any

import reflex as rx
from sqlmodel import select

from kakumi_app.models.team_model import Team
from kakumi_app.models.tournament_model import TournamentCategory


class TeamState(rx.State):
    """State for team management."""

    teams: List[Team] = []
    current_team: Optional[Team] = None
    categories: List[TournamentCategory] = []

    # Form fields
    name: str = ""
    dojo: str = ""
    category_id: str = ""  # string for select
    is_active: bool = True

    # UI state
    is_editing: bool = False
    show_form: bool = False
    error_message: str = ""
    success_message: str = ""

    # Search/filter
    search_query: str = ""

    def load_teams(self):
        """Load all teams from database."""
        with rx.session() as session:
            self.teams = session.exec(select(Team)).all()
            self.categories = session.exec(select(TournamentCategory)).all()

    def filter_teams(self):
        """Filter teams by search query."""
        if not self.search_query:
            self.load_teams()
            return

        query = self.search_query.lower()
        with rx.session() as session:
            all_teams = session.exec(select(Team)).all()
            self.teams = [
                t
                for t in all_teams
                if query in t.name.lower() or (t.dojo and query in t.dojo.lower())
            ]

    def set_form_values(self, _: Any, team: Optional[Team] = None):
        """Set form values for editing or creating."""
        if team:
            self.current_team = team
            self.is_editing = True
            self.name = team.name
            self.dojo = team.dojo or ""
            self.category_id = str(team.category_id)
            self.is_active = team.is_active
        else:
            self.current_team = None
            self.is_editing = False
            self.reset_form()

        self.show_form = True
        self.error_message = ""
        self.success_message = ""

    def reset_form(self):
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

    def save_team(self):
        """Save team (create or update)."""
        if not self.validate_form():
            return

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
                    self.error_message = "Team not found"
                    return

                for key, value in team_data.items():
                    setattr(team, key, value)

                session.add(team)
                session.commit()
                self.success_message = f"Team '{team.name}' updated successfully"
            else:
                # Check duplicate name
                existing = session.exec(
                    select(Team).where(Team.name == self.name)
                ).first()
                if existing:
                    self.error_message = f"Team with name '{self.name}' already exists"
                    return

                team = Team(**team_data)
                session.add(team)
                session.commit()
                self.success_message = f"Team '{team.name}' created successfully"

            session.commit()

        self.show_form = False
        self.load_teams()

    def delete_team(self, team_id: int):
        """Delete team by ID."""
        with rx.session() as session:
            team = session.get(Team, team_id)
            if team:
                session.delete(team)
                session.commit()
                self.success_message = f"Team '{team.name}' deleted"
                self.load_teams()
            else:
                self.error_message = "Team not found"

    def cancel_form(self):
        """Cancel form and hide it."""
        self.show_form = False
        self.error_message = ""
        self.success_message = ""
