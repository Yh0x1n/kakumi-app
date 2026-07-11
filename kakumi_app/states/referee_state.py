"""
Referee State
Manages CRUD operations for referees.
"""

import base64
import binascii
import json
from typing import Any, Optional

import reflex as rx
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from kakumi_app.models.referee_model import Referee
from kakumi_app.services.export_service import ExportService
from kakumi_app.services.import_service import ImportService


class RefereeState(rx.State):
    """State for referee management."""

    # Shared CRUD UI vars (mirrored for Reflex state registration)
    is_editing: bool = False
    show_form: bool = False
    error_message: str = ""
    search_query: str = ""
    current_page: int = 1
    page_size: int = 10

    referees: list[dict[str, Any]] = []
    current_referee: Optional[dict[str, Any]] = None

    # Form fields
    name: str = ""
    license_number: str = ""
    license_level: str = "NACIONAL"
    role: str = "ÁRBITRO"
    tatami_certified: str = ""  # JSON string
    is_available: bool = True
    dojo: str = ""
    email: str = ""
    phone: str = ""

    # Import / Export UI state
    show_import_panel: bool = False
    import_content: str = ""
    import_file_name: str = ""
    import_file_type: str = "xlsx"
    import_success_count: int = 0
    import_error_count: int = 0
    import_error_messages: list[str] = []
    export_content: str = ""

    # ── Translation helpers ──────────────────────────────────────────


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
    @staticmethod
    def _normalize_license_level(level: str) -> str:
        """Convert display Español license_level to DB English."""
        normalized = (level or "").strip().upper()
        if normalized == "NACIONAL":
            return "NATIONAL"
        if normalized == "INTERNACIONAL":
            return "INTERNATIONAL"
        return normalized

    @staticmethod
    def _display_license_level(level: str) -> str:
        """Convert DB English license_level to display Español."""
        normalized = (level or "").strip().upper()
        if normalized == "NATIONAL":
            return "NACIONAL"
        if normalized == "INTERNATIONAL":
            return "INTERNACIONAL"
        return normalized

    @staticmethod
    def _normalize_role(role: str) -> str:
        """Convert display Español role to DB English."""
        normalized = (role or "").strip().upper()
        if normalized == "ÁRBITRO" or normalized == "REFEREE":
            return "REFEREE"
        if normalized == "JUEZ":
            return "JUDGE"
        if normalized == "OFICIAL DE MESA":
            return "TABLE_OFFICIAL"
        if normalized == "SUPERVISOR (KANSA)":
            return "SUPERVISOR"
        # REFEREE, JUDGE, TABLE_OFFICIAL, SUPERVISOR passthrough
        return normalized

    @staticmethod
    def _display_role(role: str) -> str:
        """Convert DB English role to display Español."""
        normalized = (role or "").strip().upper()
        if normalized == "REFEREE":
            return "ÁRBITRO"
        if normalized == "JUDGE":
            return "JUEZ"
        if normalized == "TABLE_OFFICIAL":
            return "OFICIAL DE MESA"
        if normalized == "SUPERVISOR":
            return "SUPERVISOR (KANSA)"
        # REFEREE passthrough
        return normalized

    def _build_export_filename(self) -> str:
        """Return the downloadable export filename."""
        return "referees.xlsx"

    def _import_from_content(self) -> tuple[int, int, list[str]]:
        """Dispatch import using current XLSX payload."""
        try:
            workbook_bytes = base64.b64decode(self.import_content, validate=True)
        except (binascii.Error, ValueError):
            workbook_bytes = self.import_content.encode("utf-8")
        return ImportService.import_referees_xlsx(workbook_bytes)

    async def _finalize_import(self) -> Any:
        """Run import from current content and update UI state."""
        success, errors, messages = self._import_from_content()

        self.import_success_count = success
        self.import_error_count = errors
        self.import_error_messages = messages

        if errors:
            self.error_message = "Importación con errores: revisa el detalle"
        else:
            self.error_message = ""

        await self.load_referees()
        self.show_import_panel = False
        message = f"Importación finalizada: {success} correctos, {errors} errores"
        if errors > 0:
            return rx.toast.warning(message)
        return rx.toast.success(message)

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
        await self.load_referees()

    def referee_availability_label(self, referee: dict[str, Any]) -> str:
        """Return UI label for referee availability flag."""
        return "Disponible" if referee.get("is_available", True) else "No disponible"

    license_number_options: list[str] = ["A", "B", "C"]

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
            self.license_level = self._display_license_level(
                referee.get("license_level", "NATIONAL")
            )
            self.role = self._display_role(referee.get("role", "REFEREE"))
            tatami_val = referee.get("tatami_certified")
            if isinstance(tatami_val, list):
                self.tatami_certified = json.dumps(tatami_val)
            else:
                self.tatami_certified = tatami_val or ""
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
        self.license_level = "NACIONAL"
        self.role = "ÁRBITRO"
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

        normalized_level = self._normalize_license_level(self.license_level)
        if normalized_level not in ["NATIONAL", "INTERNATIONAL"]:
            self.error_message = "License level must be NACIONAL or INTERNACIONAL"
            return False

        normalized_role = self._normalize_role(self.role)
        if normalized_role not in ["REFEREE", "JUDGE", "TABLE_OFFICIAL", "SUPERVISOR"]:
            self.error_message = "Invalid role"
            return False

        if self.tatami_certified:
            try:
                parsed_tatami = json.loads(self.tatami_certified)
            except json.JSONDecodeError:
                self.error_message = "Tatami certified must be valid JSON array"
                return False
            if not isinstance(parsed_tatami, list):
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
            "license_level": self._normalize_license_level(self.license_level),
            "role": self._normalize_role(self.role),
            "tatami_certified": self.tatami_certified or None,
            "is_available": self.is_available,
            "dojo": self.dojo or None,
            "email": self.email or None,
            "phone": self.phone or None,
        }

        with rx.session() as session:
            try:
                if self.is_editing and self.current_referee:
                    # Update existing
                    referee_id = self.current_referee.get("id")
                    referee = (
                        session.get(Referee, int(referee_id)) if referee_id else None
                    )
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
            except SQLAlchemyError:
                session.rollback()
                return rx.toast.error("Error al guardar árbitro")

        self.show_form = False
        await self.load_referees()
        return rx.toast.success(success_message)

    @rx.event
    async def delete_referee(self, referee_id: int) -> Any:
        """Delete referee by ID."""
        with rx.session() as session:
            try:
                referee = session.get(Referee, referee_id)
                if not referee:
                    return rx.toast.error("Referee not found")

                referee_name = referee.name
                session.delete(referee)
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                return rx.toast.error("Error al eliminar árbitro")

        await self.load_referees()
        return rx.toast.success(f"Referee '{referee_name}' deleted")

    @rx.event
    def cancel_form(self) -> None:
        """Cancel form and hide it using shared mixin logic."""
        self.show_form = False
        self.error_message = ""

    @rx.event
    async def import_referees(self) -> Any:
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
        """Read an uploaded XLSX file and import referees from it."""
        if not files:
            self.error_message = "Selecciona un archivo XLSX antes de importar"
            return rx.toast.error(self.error_message)

        uploaded_file = files[0]
        self.import_file_name = uploaded_file.filename
        filename = uploaded_file.filename.lower()
        if filename.endswith(".xlsx"):
            self.import_file_type = "xlsx"
        else:
            self.error_message = (
                "Formato no soportado. Usa .xlsx; .xls no está soportado."
            )
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
    def export_referees(self) -> Any:
        """Export referees as a downloadable XLSX file."""
        workbook_bytes = ExportService.export_referees_xlsx()
        self.export_content = base64.b64encode(workbook_bytes).decode("ascii")
        return [
            rx.toast.success("Exportación de árbitros generada"),
            rx.download(
                data=workbook_bytes,
                mime_type=(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
                filename=self._build_export_filename(),
            ),
        ]
