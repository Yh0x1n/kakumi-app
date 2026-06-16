"""Tournament CRUD state used by registries pages."""

from __future__ import annotations

import calendar as _calendar
import contextlib
import datetime
from typing import Any

import reflex as rx
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from kakumi_app.models.tournament_model import (
    Match,
    Tatami,
    Tournament,
    TournamentCategory,
    TournamentStatus,
)


# ── Date format helpers (module-level) ──
def _iso_to_display(iso_str: str) -> str:
    """Convert '2026-06-07' → '07/06/2026'. Return '' on failure."""
    if not iso_str:
        return ""
    try:
        d = datetime.datetime.strptime(iso_str, "%Y-%m-%d").date()
        return d.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return ""


def _display_to_date(display_str: str) -> datetime.date | None:
    """Convert '07/06/2026' → date(2026, 6, 7). Return None on failure.

    Accepts 'DD-MM-YYYY' by normalising dashes to slashes.
    """
    if not display_str or not isinstance(display_str, str):
        return None
    normalised = display_str.replace("-", "/")
    try:
        return datetime.datetime.strptime(normalised, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


def _date_to_iso(d: datetime.date) -> str:
    """Convert date → '2026-06-07'."""
    return d.isoformat()


def _build_day_cells(
    year: int, month: int, selected_display: str
) -> list[dict[str, Any]]:
    """Build a flat list of day cell descriptors for the month grid.

    Each item has:
        day: int (0 for filler/empty cells)
        is_current_month: bool
        is_selected: bool
        label: str (day number or "")

    Uses calendar.monthcalendar for proper week alignment.
    """
    cal = _calendar.Calendar(6).monthdayscalendar(year, month)
    selected_date: datetime.date | None = None
    if selected_display:
        with contextlib.suppress(ValueError, TypeError):
            selected_date = datetime.datetime.strptime(
                selected_display, "%d/%m/%Y"
            ).date()

    cells: list[dict[str, Any]] = []
    for week in cal:
        for day in week:
            is_current = day != 0
            date_obj = datetime.date(year, month, day) if is_current else None
            is_selected = (
                selected_date is not None
                and date_obj is not None
                and date_obj == selected_date
            )
            cells.append(
                {
                    "day": day,
                    "is_current_month": is_current,
                    "is_selected": is_selected,
                    "label": str(day) if is_current else "",
                }
            )
    return cells


class TournamentCrudState(rx.State):
    """State for tournament CRUD screens in registries module."""

    is_editing: bool = False
    show_form: bool = False
    error_message: str = ""
    search_query: str = ""
    current_page: int = 1
    page_size: int = 10

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

    tournaments: list[dict[str, Any]] = []
    current_tournament: dict[str, Any] | None = None

    name: str = ""
    venue: str = ""
    start_date: str = ""
    end_date: str = ""
    tatami_count: str = "1"
    status: str = TournamentStatus.PLANIFICADO.value
    created_by_id: str = ""

    # ── Calendar popover state ──
    show_calendar: bool = False
    calendar_target: str = ""  # "start" or "end"
    calendar_month: int = 0  # 0 = uninitialized
    calendar_year: int = 0  # 0 = uninitialized

    @rx.var
    def calendar_day_cells(self) -> list[dict[str, Any]]:
        """Computed day cells for the calendar popover grid.

        Depends on calendar_month, calendar_year, and the active
        date field (start_date or end_date based on calendar_target).
        """
        if self.calendar_month == 0 or self.calendar_year == 0:
            return []
        display = self.start_date if self.calendar_target == "start" else self.end_date
        return _build_day_cells(self.calendar_year, self.calendar_month, display)

    @rx.var
    def calendar_month_name(self) -> str:
        """Spanish month name for the current calendar_month."""
        names = [
            "",
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ]
        if 1 <= self.calendar_month <= 12:
            return names[self.calendar_month]
        return ""

    def _serialize_tournament(self, tournament: Tournament) -> dict[str, Any]:
        """Return JSON-safe tournament row for CRUD list and edit flow."""
        return {
            "id": tournament.id,
            "name": tournament.name,
            "venue": tournament.venue,
            "status": tournament.status,
            "start_date": tournament.start_date.isoformat(),
            "end_date": tournament.end_date.isoformat(),
            "start_date_display": _iso_to_display(tournament.start_date.isoformat()),
            "end_date_display": _iso_to_display(tournament.end_date.isoformat()),
            "tatami_count": tournament.tatami_count,
            "created_by_id": tournament.created_by_id,
        }

    # ── Calendar popover event handlers ──

    @rx.event
    def toggle_calendar(self, target: str) -> None:
        """Toggle calendar popover for a specific date field."""
        if self.show_calendar and self.calendar_target == target:
            self.show_calendar = False
            self.calendar_target = ""
            return
        self.show_calendar = True
        self.calendar_target = target
        if self.calendar_month == 0 or self.calendar_year == 0:
            now = datetime.date.today()
            self.calendar_month = now.month
            self.calendar_year = now.year

    @rx.event
    def calendar_prev_month(self) -> None:
        """Navigate calendar to previous month with year wrap."""
        if self.calendar_month == 1:
            self.calendar_month = 12
            self.calendar_year -= 1
        else:
            self.calendar_month -= 1

    @rx.event
    def calendar_next_month(self) -> None:
        """Navigate calendar to next month with year wrap."""
        if self.calendar_month == 12:
            self.calendar_month = 1
            self.calendar_year += 1
        else:
            self.calendar_month += 1

    @rx.event
    def select_calendar_day(self, day: int) -> None:
        """Select a day from the calendar popover. Set date and close."""
        day_int = int(day)
        date_obj = datetime.date(self.calendar_year, self.calendar_month, day_int)
        display_val = date_obj.strftime("%d/%m/%Y")
        if self.calendar_target == "start":
            self.start_date = display_val
        elif self.calendar_target == "end":
            self.end_date = display_val
        self.show_calendar = False
        self.calendar_target = ""

    @rx.event
    def close_calendar(self) -> None:
        """Close the calendar popover unconditionally. Used by backdrop click."""
        self.show_calendar = False
        self.calendar_target = ""

    @rx.event
    async def initialize_registry_view(self) -> None:
        """Initialize tournament registries page state."""
        self.show_form = False
        self.error_message = ""
        self.search_query = ""
        await self.load_tournaments()

    @rx.event
    async def load_tournaments(self) -> None:
        """Load all tournaments from database."""
        with rx.session() as session:
            tournaments = session.exec(select(Tournament)).all()
            self.tournaments = [
                self._serialize_tournament(tournament) for tournament in tournaments
            ]

    @rx.event
    async def filter_tournaments(self) -> None:
        """Filter tournaments by name, venue, or status."""
        if not self.search_query:
            await self.load_tournaments()
            return

        query = self.search_query.lower()
        with rx.session() as session:
            tournaments = session.exec(select(Tournament)).all()
            self.tournaments = [
                self._serialize_tournament(tournament)
                for tournament in tournaments
                if query in tournament.name.lower()
                or query in tournament.venue.lower()
                or query in tournament.status.lower()
            ]

    @rx.event
    def set_form_values(
        self,
        _: Any,
        tournament: dict[str, Any] | None = None,
    ) -> None:
        """Set form values for edit or create modes."""
        if tournament:
            self.current_tournament = tournament
            self._set_form_open(editing=True)
            self.name = tournament.get("name", "")
            self.venue = tournament.get("venue", "")
            self.start_date = _iso_to_display(tournament.get("start_date", ""))
            self.end_date = _iso_to_display(
                tournament.get("end_date") or tournament.get("start_date", "")
            )
            self.tatami_count = str(tournament.get("tatami_count") or "1")
            created_by_id = tournament.get("created_by_id")
            self.created_by_id = str(created_by_id) if created_by_id else ""
            return

        self.current_tournament = None
        self._set_form_open(editing=False)
        self.reset_form()

    def reset_form(self) -> None:
        """Reset form fields to defaults."""
        self.name = ""
        self.venue = ""
        self.start_date = ""
        self.end_date = ""
        self.tatami_count = "1"
        self.created_by_id = ""

    def _validate_form(self) -> bool:
        """Validate required tournament form fields."""
        if not self.name.strip():
            self.error_message = "Name is required"
            return False

        if not self.venue.strip():
            self.error_message = "Venue is required"
            return False

        if not self.start_date or not self.end_date:
            self.error_message = "Start and end dates are required"
            return False

        return True

    @rx.event
    async def save_tournament(self) -> Any:  # noqa: C901
        """Create or update tournament."""
        if not self._validate_form():
            return

        start_date = _display_to_date(self.start_date)
        end_date = _display_to_date(self.end_date)
        if start_date is None or end_date is None:
            self.error_message = "Invalid date format (DD/MM/YYYY)"
            return

        try:
            tatami_count = int(self.tatami_count) if self.tatami_count else 1
        except ValueError:
            self.error_message = "Tatami count must be a number"
            return

        created_by_id: int | None = None
        if self.created_by_id:
            try:
                created_by_id = int(self.created_by_id)
            except ValueError:
                self.error_message = "Creator ID must be a number"
                return

        tournament_data = {
            "name": self.name.strip(),
            "venue": self.venue.strip(),
            "start_date": start_date,
            "end_date": end_date,
            "tatami_count": tatami_count,
            "created_by_id": created_by_id,
        }

        with rx.session() as session:
            if self.is_editing and self.current_tournament:
                tournament_id = self.current_tournament.get("id")
                tournament = (
                    session.get(Tournament, int(tournament_id))
                    if tournament_id
                    else None
                )
                if not tournament:
                    return rx.toast.error("Tournament not found")

                try:
                    tournament_data["status"] = tournament.status
                    for key, value in tournament_data.items():
                        setattr(tournament, key, value)

                    session.add(tournament)
                    session.commit()
                    success_message = (
                        f"Tournament '{tournament.name}' updated successfully"
                    )
                except SQLAlchemyError:
                    session.rollback()
                    self.error_message = "Error al guardar torneo"
                    return rx.toast.error(self.error_message)
            else:
                try:
                    existing = session.exec(
                        select(Tournament).where(Tournament.name == self.name.strip())
                    ).first()
                    if existing:
                        return rx.toast.error(
                            f"Tournament with name '{self.name}' already exists"
                        )

                    tournament = Tournament(
                        **tournament_data,
                        status=TournamentStatus.PLANIFICADO.value,
                    )
                    session.add(tournament)
                    session.commit()
                    success_message = (
                        f"Tournament '{tournament.name}' created successfully"
                    )
                except SQLAlchemyError:
                    session.rollback()
                    self.error_message = "Error al guardar torneo"
                    return rx.toast.error(self.error_message)

        self.show_form = False
        await self.load_tournaments()
        return rx.toast.success(success_message)

    @rx.event
    async def delete_tournament(self, tournament_id: int) -> Any:
        """Delete tournament when it has no dependent records."""
        with rx.session() as session:
            tournament = session.get(Tournament, tournament_id)
            if not tournament:
                return rx.toast.error("Tournament not found")

            if tournament.status not in {
                TournamentStatus.PLANIFICADO.value,
                TournamentStatus.ARCHIVADO.value,
            }:
                self.error_message = (
                    f"No se puede eliminar torneo en estado {tournament.status}"
                )
                return rx.toast.error(self.error_message)

            has_categories = session.exec(
                select(TournamentCategory.id).where(
                    TournamentCategory.tournament_id == tournament_id
                )
            ).first()
            has_matches = session.exec(
                select(Match.id).where(Match.tournament_id == tournament_id)
            ).first()
            has_tatamis = session.exec(
                select(Tatami.id).where(Tatami.tournament_id == tournament_id)
            ).first()

            if has_categories or has_matches or has_tatamis:
                self.error_message = (
                    "No se puede eliminar torneo con categorías, matches o tatamis "
                    "relacionados"
                )
                return rx.toast.error(self.error_message)

            tournament_name = tournament.name
            session.delete(tournament)
            session.commit()

        await self.load_tournaments()
        return rx.toast.success(f"Tournament '{tournament_name}' deleted")

    @rx.event
    def cancel_form(self) -> None:
        """Cancel tournament form using shared mixin behavior."""
        self.show_form = False
        self.error_message = ""
