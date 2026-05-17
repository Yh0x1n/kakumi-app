"""
Import State
Manages file upload and import process for athletes.
"""

import base64
import binascii

import reflex as rx

from kakumi_app.services.import_service import ImportService


class ImportState(rx.State):
    """State for import functionality."""

    # File content
    file_content: str = ""
    file_name: str = ""
    file_type: str = ""  # "xlsx"

    # Import results
    is_importing: bool = False
    success_count: int = 0
    error_count: int = 0
    error_messages: list[str] = []

    # UI state
    show_results: bool = False
    error_message: str = ""

    @rx.event
    async def handle_upload(self, files: list[rx.UploadFile]):
        """Handle file upload."""
        if not files:
            return

        file = files[0]
        self.file_name = file.filename

        # Determine file type
        if file.filename.endswith(".xlsx"):
            self.file_type = "xlsx"
        else:
            self.error_message = "Unsupported file type. Please upload XLSX."
            return

        # Read file content
        upload_data = await file.read()
        content = base64.b64encode(upload_data).decode("ascii") if upload_data else ""
        if content:
            self.file_content = content
            self.error_message = ""
        else:
            self.error_message = "Failed to read file content."

    @rx.event
    def import_athletes(self):
        """Import athletes from uploaded file."""
        if not self.file_content:
            self.error_message = "No file uploaded"
            return

        self.is_importing = True
        self.error_message = ""

        if self.file_type != "xlsx":
            self.is_importing = False
            self.error_message = "Invalid file type"
            return

        try:
            workbook_bytes = base64.b64decode(self.file_content, validate=True)
        except (binascii.Error, ValueError):
            self.is_importing = False
            self.error_message = "Invalid file content"
            return

        success, errors, error_list = ImportService.import_athletes_xlsx(workbook_bytes)

        self.success_count = success
        self.error_count = errors
        self.error_messages = error_list
        self.is_importing = False
        self.show_results = True

    @rx.event
    def reset_import(self):
        """Reset import state."""
        self.file_content = ""
        self.file_name = ""
        self.file_type = ""
        self.success_count = 0
        self.error_count = 0
        self.error_messages = []
        self.show_results = False
        self.error_message = ""
