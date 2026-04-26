"""
Referee State
Manages CRUD operations for referees.
"""

import json
from typing import Any, Optional

import reflex as rx
from sqlmodel import select

from kakumi_app.models.referee_model import Referee
from kakumi_app.states.base_crud_state import CrudStateMixin


class RefereeState(CrudStateMixin, rx.State):
    """State for referee management."""

    # Shared CRUD UI vars (mirrored for Reflex state registration)
    is_editing: bool = CrudStateMixin.is_editing
    show_form: bool = CrudStateMixin.show_form
    error_message: str = CrudStateMixin.error_message
    search_query: str = CrudStateMixin.search_query

    referees: list[dict[str, Any]] = []
    current_referee: Optional[dict[str, Any]] = None

    # Form fields
    name: str = ""
    license_number: str = ""
    license_level: str = "NATIONAL"
    role: str = "REFEREE"
    tatami_certified: str = ""  # JSON string
    is_available: bool = True
    dojo: str = ""
    email: str = ""
    phone: str = ""

    @rx.event
    async def load_referees(self) -> None:
        """Load all referees from database."""
        with rx.session() as session:
            referees = session.exec(select(Referee)).all()
            self.referees = [referee.model_dump(mode="json") for referee in referees]

    @rx.event
    async def filter_referees(self) -> None:
        """Filter referees by search query."""
        if not self.search_query:
            await self.load_referees()
            return

        query = self.search_query.lower()
        with rx.session() as session:
            all_referees = session.exec(select(Referee)).all()
            self.referees = [
                r.model_dump(mode="json")
                for r in all_referees
                if query in r.name.lower()
                or (r.email and query in r.email.lower())
                or (r.dojo and query in r.dojo.lower())
                or query in r.license_number.lower()
            ]

    @rx.event
    def set_form_values(
        self,
        _: Any,
        referee: Optional[dict[str, Any]] = None,
    ) -> None:
        """Set form values for editing or creating."""
        if referee:
            self.current_referee = referee
            self._set_form_open(editing=True)
            self.name = referee.get("name", "")
            self.license_number = referee.get("license_number", "")
            self.license_level = referee.get("license_level", "NATIONAL")
            self.role = referee.get("role", "REFEREE")
            self.tatami_certified = referee.get("tatami_certified") or ""
            self.is_available = bool(referee.get("is_available", True))
            self.dojo = referee.get("dojo") or ""
            self.email = referee.get("email") or ""
            self.phone = referee.get("phone") or ""
        else:
            self.current_referee = None
            self._set_form_open(editing=False)
            self.reset_form()

    def reset_form(self) -> None:
        """Reset form fields."""
        self.name = ""
        self.license_number = ""
        self.license_level = "NATIONAL"
        self.role = "REFEREE"
        self.tatami_certified = ""
        self.is_available = True
        self.dojo = ""
        self.email = ""
        self.phone = ""

    def validate_form(self) -> bool:
        """Validate form fields."""
        if not self.name or len(self.name) < 2 or len(self.name) > 255:
            self.error_message = "Name must be 2-255 characters"
            return False

        if not self.license_number or len(self.license_number) > 50:
            self.error_message = "License number is required (max 50 chars)"
            return False

        if self.license_level not in ["NATIONAL", "INTERNATIONAL"]:
            self.error_message = "License level must be NATIONAL or INTERNATIONAL"
            return False

        if self.role not in ["REFEREE", "JUDGE", "TABLE_OFFICIAL", "SUPERVISOR"]:
            self.error_message = "Invalid role"
            return False

        if self.tatami_certified:
            try:
                json.loads(self.tatami_certified)
            except json.JSONDecodeError:
                self.error_message = "Tatami certified must be valid JSON array"
                return False

        return True

    @rx.event
    async def save_referee(self) -> Any:
        """Save referee (create or update)."""
        if not self.validate_form():
            return

        self.error_message = ""

        referee_data = {
            "name": self.name,
            "license_number": self.license_number,
            "license_level": self.license_level,
            "role": self.role,
            "tatami_certified": self.tatami_certified or None,
            "is_available": self.is_available,
            "dojo": self.dojo or None,
            "email": self.email or None,
            "phone": self.phone or None,
        }

        with rx.session() as session:
            if self.is_editing and self.current_referee:
                # Update existing
                referee_id = self.current_referee.get("id")
                referee = session.get(Referee, int(referee_id)) if referee_id else None
                if not referee:
                    return rx.toast.error("Referee not found")

                for key, value in referee_data.items():
                    setattr(referee, key, value)

                session.add(referee)
                session.commit()
                success_message = f"Referee '{referee.name}' updated successfully"
            else:
                # Check duplicate name
                existing = session.exec(
                    select(Referee).where(Referee.name == self.name)
                ).first()
                if existing:
                    return rx.toast.error(
                        f"Referee with name '{self.name}' already exists"
                    )

                referee = Referee(**referee_data)
                session.add(referee)
                session.commit()
                success_message = f"Referee '{referee.name}' created successfully"

        self.show_form = False
        await self.load_referees()
        return rx.toast.success(success_message)

    @rx.event
    async def delete_referee(self, referee_id: int) -> Any:
        """Delete referee by ID."""
        with rx.session() as session:
            referee = session.get(Referee, referee_id)
            if not referee:
                return rx.toast.error("Referee not found")

            referee_name = referee.name
            session.delete(referee)
            session.commit()

        await self.load_referees()
        return rx.toast.success(f"Referee '{referee_name}' deleted")

    @rx.event
    def cancel_form(self) -> None:
        """Cancel form and hide it using shared mixin logic."""
        CrudStateMixin.cancel_form(self)
