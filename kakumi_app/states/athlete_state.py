"""
Athlete State
Manages CRUD operations for athletes.
"""

import datetime
import base64
import binascii
from typing import Any, Optional

import reflex as rx
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.services.export_service import ExportService
from kakumi_app.services.import_service import ImportService
from kakumi_app.states.base_crud_state import CrudStateMixin


class AthleteState(CrudStateMixin, rx.State):
    """State for athlete management."""

    # Shared CRUD UI vars (mirrored for Reflex state registration)
    is_editing: bool = CrudStateMixin.is_editing
    show_form: bool = CrudStateMixin.show_form
    error_message: str = CrudStateMixin.error_message
    search_query: str = CrudStateMixin.search_query
    current_page: int = CrudStateMixin.current_page
    page_size: int = CrudStateMixin.page_size

    athletes: list[dict[str, Any]] = []
    current_athlete: Optional[dict[str, Any]] = None

    # Form fields
    name: str = ""
    email: str = ""
    date_of_birth: str = ""
    gender: str = "MASCULINO"
    weight_kg: str = ""
    belt_rank: str = ""
    dojo: str = ""
    nationality: str = ""
    license_number: str = ""
    is_active: bool = True

    # Import / Export UI state
    show_import_panel: bool = False
    import_content: str = ""
    import_file_name: str = ""
    import_file_type: str = "xlsx"
    import_success_count: int = 0
    import_error_count: int = 0
    import_error_messages: list[str] = []
    export_content: str = ""

    @staticmethod
    def _normalize_gender(gender: str) -> str:
        """Normalize legacy Spanish values to the canonical enum values."""
        normalized = (gender or "").strip().upper()
        if normalized == "MASCULINO":
            return "MALE"
        if normalized == "FEMENINO":
            return "FEMALE"
        return normalized or "MALE"

    @staticmethod
    def _display_gender(gender: str) -> str:
        """Convert DB gender (MALE/FEMALE) to display Español."""
        normalized = (gender or "").strip().upper()
        if normalized == "MALE":
            return "MASCULINO"
        if normalized == "FEMALE":
            return "FEMENINO"
        return normalized

    def _build_export_filename(self) -> str:
        """Return the downloadable export filename."""
        return "athletes.xlsx"

    def _import_from_content(self) -> tuple[int, int, list[str]]:
        """Dispatch import using current XLSX payload."""
        try:
            workbook_bytes = base64.b64decode(self.import_content, validate=True)
        except (binascii.Error, ValueError):
            workbook_bytes = self.import_content.encode("utf-8")
        return ImportService.import_athletes_xlsx(workbook_bytes)

    async def _finalize_import(self) -> Any:
        """Run import from current content and update UI state."""
        success, errors, messages = self._import_from_content()

        self.import_success_count = success
        self.import_error_count = errors
        self.import_error_messages = messages

        if errors:
            self.error_message = "Importación con errores: revisá el detalle"
        else:
            self.error_message = ""

        await self.load_athletes()
        self.show_import_panel = False
        message = f"Importación finalizada: {success} correctos, {errors} errores"
        if errors > 0:
            return rx.toast.warning(message)
        return rx.toast.success(message)

    @rx.event
    async def load_athletes(self) -> None:
        """Load all athletes from database."""
        with rx.session() as session:
            athletes = session.exec(select(Athlete)).all()
            self.athletes = [athlete.model_dump(mode="json") for athlete in athletes]

    @rx.event
    async def filter_athletes(self) -> None:
        """Filter athletes by search query."""
        if not self.search_query:
            await self.load_athletes()
            return

        query = self.search_query.lower()
        with rx.session() as session:
            all_athletes = session.exec(select(Athlete)).all()
            self.athletes = [
                a.model_dump(mode="json")
                for a in all_athletes
                if query in a.name.lower()
                or (a.email and query in a.email.lower())
                or (a.dojo and query in a.dojo.lower())
            ]

    @rx.event
    async def initialize_registry_view(self) -> None:
        """Prepare CRUD route state on page load."""
        self.show_form = False
        self.show_import_panel = False
        self.error_message = ""
        self.reset_filters()
        self.import_content = ""
        self.import_file_name = ""
        self.import_file_type = "xlsx"
        self.import_success_count = 0
        self.import_error_count = 0
        self.import_error_messages = []
        self.export_content = ""
        await self.load_athletes()

    def athlete_status_label(self, athlete: dict[str, Any]) -> str:
        """Return UI label for athlete active flag."""
        return "Activo" if athlete.get("is_active", True) else "Inactivo"

    @rx.event
    def set_form_values(
        self,
        _: Any,
        athlete: Optional[dict[str, Any]] = None,
    ) -> None:
        """Set form values for editing or creating."""
        if athlete:
            self.current_athlete = athlete
            self._set_form_open(editing=True)
            self.name = athlete.get("name", "")
            self.email = athlete.get("email") or ""
            self.date_of_birth = athlete.get("date_of_birth") or ""
            self.gender = self._display_gender(athlete.get("gender", "MALE"))
            weight_kg = athlete.get("weight_kg")
            self.weight_kg = str(weight_kg) if weight_kg else ""
            self.belt_rank = athlete.get("belt_rank") or ""
            self.dojo = athlete.get("dojo") or ""
            self.nationality = athlete.get("nationality") or ""
            self.license_number = athlete.get("license_number") or ""
            self.is_active = bool(athlete.get("is_active", True))
        else:
            self.current_athlete = None
            self._set_form_open(editing=False)
            self.reset_form()

    def reset_form(self) -> None:
        """Reset form fields."""
        self.name = ""
        self.email = ""
        self.date_of_birth = ""
        self.gender = "MASCULINO"
        self.weight_kg = ""
        self.belt_rank = ""
        self.dojo = ""
        self.nationality = ""
        self.license_number = ""
        self.is_active = True

    def validate_form(self) -> bool:
        """Validate form fields."""
        validators = (
            self._validate_name,
            self._validate_date_of_birth,
            self._validate_gender,
            self._validate_weight,
            self._validate_belt_rank,
        )
        for validate in validators:
            if not validate():
                return False
        return True

    def _validate_name(self) -> bool:
        """Validate athlete name constraints."""
        if not self.name or len(self.name) < 2 or len(self.name) > 255:
            self.error_message = "Name must be 2-255 characters"
            return False
        return True

    def _validate_date_of_birth(self) -> bool:
        """Validate date input and prevent future birth dates."""
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
        return True

    def _validate_gender(self) -> bool:
        """Validate gender value against supported enum values."""
        normalized_gender = self._normalize_gender(self.gender)
        if normalized_gender not in ["MALE", "FEMALE"]:
            self.error_message = "Gender must be MALE or FEMALE"
            return False
        # Keep display value (Español) in self.gender; normalize only for DB
        return True

    def _validate_weight(self) -> bool:
        """Validate optional weight field range and numeric format."""
        if self.weight_kg:
            try:
                weight = float(self.weight_kg)
                if weight < 40.0 or weight > 120.0:
                    self.error_message = "Weight must be between 40.0 and 120.0 kg"
                    return False
            except ValueError:
                self.error_message = "Weight must be a number"
                return False
        return True

    def _validate_belt_rank(self) -> bool:
        """Validate optional belt rank for Kyu/Dan or belt colors."""
        if self.belt_rank and not ImportService.validate_belt_rank(self.belt_rank):
            self.error_message = (
                "Belt rank must be 'Kyu 1-8', 'Dan 1-10', "
                "or belt colors from 'Blanco' to 'Negro'"
            )
            return False
        return True

    @rx.event
    async def save_athlete(self) -> Any:
        """Save athlete (create or update)."""
        if not self.validate_form():
            return

        self.error_message = ""

        weight_kg = float(self.weight_kg) if self.weight_kg else None

        athlete_data = {
            "name": self.name,
            "email": self.email or None,
            "date_of_birth": datetime.datetime.strptime(
                self.date_of_birth, "%Y-%m-%d"
            ).date(),
            "gender": self._normalize_gender(self.gender),
            "weight_kg": weight_kg,
            "belt_rank": self.belt_rank or None,
            "dojo": self.dojo or None,
            "nationality": self.nationality or None,
            "license_number": self.license_number or None,
            "is_active": self.is_active,
        }

        with rx.session() as session:
            try:
                if self.is_editing and self.current_athlete:
                    # Update existing
                    athlete_id = self.current_athlete.get("id")
                    athlete = (
                        session.get(Athlete, int(athlete_id)) if athlete_id else None
                    )
                    if not athlete:
                        return rx.toast.error("Athlete not found")

                    for key, value in athlete_data.items():
                        setattr(athlete, key, value)

                    session.add(athlete)
                    session.commit()
                    success_message = f"Athlete '{athlete.name}' updated successfully"
                else:
                    # Check duplicate name
                    existing = session.exec(
                        select(Athlete).where(Athlete.name == self.name)
                    ).first()
                    if existing:
                        return rx.toast.error(
                            f"Athlete with name '{self.name}' already exists"
                        )

                    athlete = Athlete(**athlete_data)
                    session.add(athlete)
                    session.commit()
                    success_message = f"Athlete '{athlete.name}' created successfully"
            except SQLAlchemyError:
                session.rollback()
                return rx.toast.error("Error al guardar atleta")

        self.show_form = False
        await self.load_athletes()
        return rx.toast.success(success_message)

    @rx.event
    async def delete_athlete(self, athlete_id: int) -> Any:
        """Delete athlete by ID."""
        with rx.session() as session:
            try:
                athlete = session.get(Athlete, athlete_id)
                if not athlete:
                    return rx.toast.error("Athlete not found")

                athlete_name = athlete.name
                session.delete(athlete)
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                return rx.toast.error("Error al eliminar atleta")

        await self.load_athletes()
        return rx.toast.success(f"Athlete '{athlete_name}' deleted")

    @rx.event
    def cancel_form(self) -> None:
        """Cancel form and hide it using shared mixin logic."""
        CrudStateMixin.cancel_form(self)

    @rx.event
    async def import_athletes(self) -> Any:
        """Open file flow, or import preloaded content for compatibility."""
        if self.import_content.strip():
            return await self._finalize_import()
        self.show_import_panel = True
        self.error_message = ""
        return None

    @rx.event
    def close_import_panel(self) -> None:
        """Close import panel without mutating previous import results."""
        self.show_import_panel = False

    @rx.event
    async def handle_import_upload(self, files: list[rx.UploadFile]) -> Any:
        """Read an uploaded XLSX file and import athletes from it."""
        if not files:
            self.error_message = "Seleccioná un archivo XLSX antes de importar"
            return rx.toast.error(self.error_message)

        uploaded_file = files[0]
        self.import_file_name = uploaded_file.filename
        filename = uploaded_file.filename.lower()
        if filename.endswith(".xlsx"):
            self.import_file_type = "xlsx"
        else:
            self.error_message = "Formato no soportado. Usá .xlsx; .xls no está soportado."
            return rx.toast.error(self.error_message)

        upload_data = await uploaded_file.read()
        self.import_content = (
            base64.b64encode(upload_data).decode("ascii") if upload_data else ""
        )
        if not self.import_content.strip():
            self.error_message = "El archivo está vacío o no se pudo leer"
            return rx.toast.error(self.error_message)

        return await self._finalize_import()

    @rx.event
    def export_athletes(self) -> Any:
        """Export athletes as a downloadable XLSX file."""
        workbook_bytes = ExportService.export_athletes_xlsx()
        self.export_content = base64.b64encode(workbook_bytes).decode("ascii")
        return [
            rx.toast.success("Exportación de atletas generada"),
            rx.download(
                data=workbook_bytes,
                mime_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                filename=self._build_export_filename(),
            ),
        ]
