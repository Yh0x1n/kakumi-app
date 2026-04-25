"""
Export State
Manages export of tournament results.
"""

from typing import List

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

    @rx.var
    def tournament_options(self) -> list[str]:
        """Tournament labels for select options."""
        return [f"{t.id}: {t.name}" for t in self.tournaments]

    @rx.var
    def export_preview(self) -> str:
        """Short export content preview for UI."""
        if len(self.export_content) > 500:
            return self.export_content[:500] + "..."
        return self.export_content

    @rx.event
    def load_tournaments(self):
        """Load available tournaments."""
        with rx.session() as session:
            self.tournaments = session.exec(select(Tournament)).all()

    @rx.event
    async def export_tournament_results(self):
        """Export results for selected tournament."""
        if not self.selected_tournament_id:
            return rx.toast.error("Please select a tournament")

        tournament_id = int(self.selected_tournament_id)
        self.is_exporting = True

        try:
            if self.export_format == "json":
                content = ExportService.export_tournament_results_json(tournament_id)
                filename = f"tournament_{tournament_id}_results.json"
            else:
                content = ExportService.export_tournament_results_csv(tournament_id)
                filename = f"tournament_{tournament_id}_results.csv"

            self.export_content = content
            self.export_filename = filename
            return rx.toast.success("Export generated successfully")
        except Exception as e:
            return rx.toast.error(f"Export failed: {str(e)}")
        finally:
            self.is_exporting = False

    @rx.event
    async def download_export(self):
        """Trigger download of exported file."""
        # In Reflex, we can't directly trigger downloads from backend
        # This would require a frontend workaround
        pass

    @rx.event
    def clear_export(self):
        """Clear export content."""
        self.export_content = ""
        self.export_filename = ""
