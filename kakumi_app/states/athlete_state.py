"""
Athlete State
Manages CRUD operations for athletes.
"""

import datetime
from typing import Dict, List, Optional, Any

import reflex as rx
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete


class AthleteState(rx.State):
    """State for athlete management."""

    athletes: List[Athlete] = []
    current_athlete: Optional[Athlete] = None

    # Form fields
    name: str = ""
    email: str = ""
    date_of_birth: str = ""
    gender: str = "MALE"
    weight_kg: str = ""
    belt_rank: str = ""
    dojo: str = ""
    nationality: str = ""
    license_number: str = ""
    is_active: bool = True

    # UI state
    is_editing: bool = False
    show_form: bool = False
    error_message: str = ""
    success_message: str = ""

    # Search/filter
    search_query: str = ""

    def load_athletes(self):
        """Load all athletes from database."""
        with rx.session() as session:
            self.athletes = session.exec(select(Athlete)).all()

    def filter_athletes(self):
        """Filter athletes by search query."""
        if not self.search_query:
            self.load_athletes()
            return

        query = self.search_query.lower()
        with rx.session() as session:
            all_athletes = session.exec(select(Athlete)).all()
            self.athletes = [
                a
                for a in all_athletes
                if query in a.name.lower()
                or (a.email and query in a.email.lower())
                or (a.dojo and query in a.dojo.lower())
            ]

    def set_form_values(self, _: Any, athlete: Optional[Athlete] = None):
        """Set form values for editing or creating."""
        if athlete:
            self.current_athlete = athlete
            self.is_editing = True
            self.name = athlete.name
            self.email = athlete.email or ""
            self.date_of_birth = (
                athlete.date_of_birth.isoformat() if athlete.date_of_birth else ""
            )
            self.gender = athlete.gender
            self.weight_kg = str(athlete.weight_kg) if athlete.weight_kg else ""
            self.belt_rank = athlete.belt_rank or ""
            self.dojo = athlete.dojo or ""
            self.nationality = athlete.nationality or ""
            self.license_number = athlete.license_number or ""
            self.is_active = athlete.is_active
        else:
            self.current_athlete = None
            self.is_editing = False
            self.reset_form()

        self.show_form = True
        self.error_message = ""
        self.success_message = ""

    def reset_form(self):
        """Reset form fields."""
        self.name = ""
        self.email = ""
        self.date_of_birth = ""
        self.gender = "MALE"
        self.weight_kg = ""
        self.belt_rank = ""
        self.dojo = ""
        self.nationality = ""
        self.license_number = ""
        self.is_active = True

    def validate_form(self) -> bool:
        """Validate form fields."""
        if not self.name or len(self.name) < 2 or len(self.name) > 255:
            self.error_message = "Name must be 2-255 characters"
            return False

        if not self.date_of_birth:
            self.error_message = "Date of birth is required"
            return False

        try:
            dob = datetime.datetime.strptime(self.date_of_birth, "%Y-%m-%d").date()
            if dob > datetime.date.today():
                self.error_message = "Date of birth cannot be in the future"
                return False
        except ValueError:
            self.error_message = "Invalid date format (YYYY-MM-DD)"
            return False

        if self.gender not in ["MALE", "FEMALE"]:
            self.error_message = "Gender must be MALE or FEMALE"
            return False

        if self.weight_kg:
            try:
                weight = float(self.weight_kg)
                if weight < 40.0 or weight > 120.0:
                    self.error_message = "Weight must be between 40.0 and 120.0 kg"
                    return False
            except ValueError:
                self.error_message = "Weight must be a number"
                return False

        if self.belt_rank:
            if not (
                self.belt_rank.startswith("Kyu ") or self.belt_rank.startswith("Dan ")
            ):
                self.error_message = "Belt rank must be 'Kyu 1-8' or 'Dan 1-10'"
                return False

        return True

    def save_athlete(self):
        """Save athlete (create or update)."""
        if not self.validate_form():
            return

        weight_kg = float(self.weight_kg) if self.weight_kg else None

        athlete_data = {
            "name": self.name,
            "email": self.email or None,
            "date_of_birth": datetime.datetime.strptime(
                self.date_of_birth, "%Y-%m-%d"
            ).date(),
            "gender": self.gender,
            "weight_kg": weight_kg,
            "belt_rank": self.belt_rank or None,
            "dojo": self.dojo or None,
            "nationality": self.nationality or None,
            "license_number": self.license_number or None,
            "is_active": self.is_active,
        }

        with rx.session() as session:
            if self.is_editing and self.current_athlete:
                # Update existing
                athlete = session.get(Athlete, self.current_athlete.id)
                if not athlete:
                    self.error_message = "Athlete not found"
                    return

                for key, value in athlete_data.items():
                    setattr(athlete, key, value)

                session.add(athlete)
                session.commit()
                self.success_message = f"Athlete '{athlete.name}' updated successfully"
            else:
                # Check duplicate name
                existing = session.exec(
                    select(Athlete).where(Athlete.name == self.name)
                ).first()
                if existing:
                    self.error_message = (
                        f"Athlete with name '{self.name}' already exists"
                    )
                    return

                athlete = Athlete(**athlete_data)
                session.add(athlete)
                session.commit()
                self.success_message = f"Athlete '{athlete.name}' created successfully"

            session.commit()

        self.show_form = False
        self.load_athletes()

    def delete_athlete(self, athlete_id: int):
        """Delete athlete by ID."""
        with rx.session() as session:
            athlete = session.get(Athlete, athlete_id)
            if athlete:
                session.delete(athlete)
                session.commit()
                self.success_message = f"Athlete '{athlete.name}' deleted"
                self.load_athletes()
            else:
                self.error_message = "Athlete not found"

    def cancel_form(self):
        """Cancel form and hide it."""
        self.show_form = False
        self.error_message = ""
        self.success_message = ""
