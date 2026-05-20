"""
Export Service
Handles export of tournament results and registry workbooks.
"""

import datetime
import json

import reflex as rx
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.referee_model import Referee
from kakumi_app.models.tournament_model import Match, Tournament, TournamentCategory
from kakumi_app.services.registry_excel_service import (
    build_athletes_workbook,
    build_referees_workbook,
)


class ExportService:
    """Service for exporting tournament data and registry XLSX workbooks."""

    @staticmethod
    def export_athletes_xlsx() -> bytes:
        """Export all athletes to XLSX workbook bytes."""
        with rx.session() as session:
            athletes = session.exec(select(Athlete)).all()

        return build_athletes_workbook(
            [
                {
                    "name": athlete.name,
                    "email": athlete.email,
                    "age": athlete.age,
                    "gender": athlete.gender,
                    "weight_kg": athlete.weight_kg,
                    "belt_rank": athlete.belt_rank,
                    "dojo": athlete.dojo,
                    "nationality": athlete.nationality,
                    "license_number": athlete.license_number,
                }
                for athlete in athletes
            ]
        )

    @staticmethod
    def export_tournament_results_json(tournament_id: int) -> str:
        """
        Export tournament results in JSON format per spec 9.2.
        Includes tournament info, categories, matches, and podiums.
        """
        with rx.session() as session:
            tournament = session.get(Tournament, tournament_id)
            if not tournament:
                return json.dumps({"error": "Tournament not found"})

            # Get categories for this tournament
            categories = session.exec(
                select(TournamentCategory).where(
                    TournamentCategory.tournament_id == tournament_id
                )
            ).all()

            _matches = session.exec(
                select(Match).where(Match.tournament_id == tournament_id)
            ).all()
            # penalties = session.exec(select(Penalty)...)

            # categories_data = []
            # for cat in kata_categories + kumite_categories:
            #     matches = ...

            result = {
                "tournament": {
                    "id": tournament.id,
                    "name": tournament.name,
                    "date": tournament.start_date.isoformat()
                    if tournament.start_date
                    else "",
                    "status": tournament.status,
                },
                "categories": [],  # Empty until Match/Penalty implemented
                "statistics": {
                    "total_categories": len(categories),
                    "total_matches": len(_matches),
                    "export_date": datetime.datetime.now().isoformat(),
                },
            }

            return json.dumps(result, indent=2, ensure_ascii=False)

    @staticmethod
    def export_tournament_results_csv(tournament_id: int) -> str:
        """Export tournament results in CSV format per spec 9.2.2."""
        del tournament_id
        # NOTE: Match and Penalty models are not yet implemented
        # This function returns empty until the models are created
        return ""

    @staticmethod
    def export_referees_xlsx() -> bytes:
        """Export all referees to XLSX workbook bytes."""
        with rx.session() as session:
            referees = session.exec(select(Referee)).all()

        return build_referees_workbook(
            [
                {
                    "name": referee.name,
                    "license_number": referee.license_number,
                    "license_level": referee.license_level,
                    "role": referee.role,
                    "is_available": referee.is_available,
                    "dojo": referee.dojo,
                    "email": referee.email,
                    "phone": referee.phone,
                }
                for referee in referees
            ]
        )

    @staticmethod
    def export_teams_csv() -> str:
        """Export all teams to CSV."""
        # Placeholder
        return ""
