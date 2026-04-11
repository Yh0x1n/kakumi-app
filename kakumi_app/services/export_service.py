"""
Export Service
Handles export of tournament results, athletes, and other data in JSON/CSV formats.
"""

import csv
import datetime
import io
import json
from typing import Any, Dict, List, Optional

import reflex as rx
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.referee_model import Referee
from kakumi_app.models.tournament_model import Tournament, TournamentCategory


# NOTE: Match and Penalty models are not yet implemented
# from kakumi_app.models.match_model import Match
# from kakumi_app.models.penalty_model import Penalty


class ExportService:
    """Service for exporting data in various formats."""

    @staticmethod
    def export_athletes_csv() -> str:
        """Export all athletes to CSV string."""
        with rx.session() as session:
            athletes = session.exec(select(Athlete)).all()

        output = io.StringIO()
        fieldnames = [
            "id",
            "name",
            "email",
            "date_of_birth",
            "gender",
            "weight_kg",
            "belt_rank",
            "dojo",
            "nationality",
            "license_number",
            "is_active",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for athlete in athletes:
            writer.writerow(
                {
                    "id": athlete.id,
                    "name": athlete.name,
                    "email": athlete.email,
                    "date_of_birth": athlete.date_of_birth.isoformat()
                    if athlete.date_of_birth
                    else "",
                    "gender": athlete.gender,
                    "weight_kg": athlete.weight_kg or "",
                    "belt_rank": athlete.belt_rank or "",
                    "dojo": athlete.dojo or "",
                    "nationality": athlete.nationality or "",
                    "license_number": athlete.license_number or "",
                    "is_active": athlete.is_active,
                }
            )

        return output.getvalue()

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

            # NOTE: Match and Penalty models are not yet implemented
            # matches = session.exec(select(Match)...)
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
                    "total_matches": 0,
                    "export_date": datetime.datetime.now().isoformat(),
                },
            }

            return json.dumps(result, indent=2, ensure_ascii=False)

    @staticmethod
    def export_tournament_results_csv(tournament_id: int) -> str:
        """Export tournament results in CSV format per spec 9.2.2."""
        # NOTE: Match and Penalty models are not yet implemented
        # This function returns empty until the models are created
        return ""

    @staticmethod
    def export_referees_csv() -> str:
        """Export all referees to CSV."""
        # Placeholder
        return ""

    @staticmethod
    def export_teams_csv() -> str:
        """Export all teams to CSV."""
        # Placeholder
        return ""
