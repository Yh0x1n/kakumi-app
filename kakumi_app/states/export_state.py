"""
Export State
Manages export of tournament results.
"""

from typing import List, Optional

import reflex as rx
from sqlmodel import select

from kakumi_app.models.tournament_model import Tournament
from kakumi_app.services.export_service import ExportService


class ExportState(rx.State):
    """State for export functionality."""

    tournaments: List[Tournament] = []
    selected_tournament_id: str = ""

    # Export options
    export_format: str = "json"  # "json" or "csv"

    # Results
    export_content: str = ""
    export_filename: str = ""
    is_exporting: bool = False
    error_message: str = ""

    def load_tournaments(self):
        """Load available tournaments."""
        with rx.session() as session:
            self.tournaments = session.exec(select(Tournament)).all()

    def export_tournament_results(self):
        """Export results for selected tournament."""
        if not self.selected_tournament_id:
            self.error_message = "Please select a tournament"
            return

        tournament_id = int(self.selected_tournament_id)
        self.is_exporting = True
        self.error_message = ""

        try:
            if self.export_format == "json":
                content = ExportService.export_tournament_results_json(tournament_id)
                filename = f"tournament_{tournament_id}_results.json"
            else:
                content = ExportService.export_tournament_results_csv(tournament_id)
                filename = f"tournament_{tournament_id}_results.csv"

            self.export_content = content
            self.export_filename = filename
        except Exception as e:
            self.error_message = f"Export failed: {str(e)}"
        finally:
            self.is_exporting = False

    def download_export(self):
        """Trigger download of exported file."""
        # In Reflex, we can't directly trigger downloads from backend
        # This would require a frontend workaround
        pass

    def clear_export(self):
        """Clear export content."""
        self.export_content = ""
        self.export_filename = ""
        self.error_message = ""
