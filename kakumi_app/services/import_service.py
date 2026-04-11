"""
Import Service
Handles CSV/JSON import of athletes, referees, and teams.
"""

import csv
import io
import json
import datetime
from typing import Dict, List, Optional, Tuple

import reflex as rx
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.referee_model import Referee


# NOTE: Team model not yet implemented
# from kakumi_app.models.team_model import Team, TeamMember


class ImportError(Exception):
    """Custom exception for import errors."""

    pass


class ImportService:
    """Service for importing data from CSV/JSON files."""

    @staticmethod
    def validate_date_iso8601(date_str: str) -> bool:
        """Validate date string in ISO 8601 format (YYYY-MM-DD)."""
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_country_code(code: str) -> bool:
        """Validate ISO 3166-1 alpha-3 country code (basic check)."""
        # Simple check: 3 uppercase letters
        return isinstance(code, str) and len(code) == 3 and code.isalpha()

    @staticmethod
    def validate_gender(gender: str) -> bool:
        """Validate gender field."""
        return gender.upper() in ["MALE", "FEMALE"]

    @staticmethod
    def validate_weight(weight: float) -> bool:
        """Validate weight in kg."""
        return 40.0 <= weight <= 120.0

    @staticmethod
    def validate_belt_rank(rank: str) -> bool:
        """Validate belt rank format (Kyu 1-8 or Dan 1-10)."""
        if not isinstance(rank, str):
            return False
        rank = rank.strip()
        if rank.startswith("Kyu "):
            try:
                num = int(rank.split()[1])
                return 1 <= num <= 8
            except (IndexError, ValueError):
                return False
        elif rank.startswith("Dan "):
            try:
                num = int(rank.split()[1])
                return 1 <= num <= 10
            except (IndexError, ValueError):
                return False
        return False

    @staticmethod
    def parse_athlete_row(row: Dict, row_num: int) -> Tuple[bool, Optional[Dict], str]:
        """
        Parse a single athlete row from CSV/JSON.
        Returns (success, data_dict, error_message).
        """
        errors = []
        name = row.get("name", "").strip()
        if not name or len(name) < 2 or len(name) > 255:
            errors.append("Name must be 2-255 characters")

        date_of_birth = row.get("date_of_birth", "").strip()
        if not ImportService.validate_date_iso8601(date_of_birth):
            errors.append("Invalid date_of_birth format (YYYY-MM-DD)")
        else:
            dob = datetime.datetime.strptime(date_of_birth, "%Y-%m-%d").date()
            if dob > datetime.date.today():
                errors.append("date_of_birth cannot be in the future")

        gender = row.get("gender", "").strip()
        if not ImportService.validate_gender(gender):
            errors.append("gender must be MALE or FEMALE")

        weight_str = row.get("weight_kg", "").strip()
        weight_kg = None
        if weight_str:
            try:
                weight_kg = float(weight_str)
                if not ImportService.validate_weight(weight_kg):
                    errors.append("weight_kg must be between 40.0 and 120.0")
            except ValueError:
                errors.append("weight_kg must be a number")

        belt_rank = row.get("belt_rank", "").strip()
        if belt_rank and not ImportService.validate_belt_rank(belt_rank):
            errors.append("belt_rank must be 'Kyu 1-8' or 'Dan 1-10'")

        dojo = row.get("dojo", "").strip()
        if dojo and len(dojo) > 255:
            errors.append("dojo must be less than 255 characters")

        nationality = row.get("nationality", "").strip()
        if nationality and not ImportService.validate_country_code(nationality):
            errors.append("nationality must be ISO 3166-1 alpha-3 code")

        license_number = row.get("license_number", "").strip()

        if errors:
            return False, None, f"Row {row_num}: " + "; ".join(errors)

        data = {
            "name": name,
            "email": row.get("email", "").strip() or None,
            "date_of_birth": date_of_birth,
            "gender": gender.upper(),
            "weight_kg": weight_kg,
            "belt_rank": belt_rank or None,
            "dojo": dojo or None,
            "nationality": nationality or None,
            "license_number": license_number or None,
        }
        return True, data, ""

    @staticmethod
    def import_athletes_csv(csv_content: str) -> Tuple[int, int, List[str]]:
        """
        Import athletes from CSV string.
        Returns (success_count, error_count, error_messages).
        """
        success_count = 0
        error_count = 0
        error_messages = []

        reader = csv.DictReader(io.StringIO(csv_content))
        required_fields = ["name", "date_of_birth", "gender"]

        # Check header
        if not all(field in reader.fieldnames for field in required_fields):
            return 0, 1, ["CSV missing required fields: name, date_of_birth, gender"]

        for i, row in enumerate(reader, start=2):  # row 1 is header
            success, data, error = ImportService.parse_athlete_row(row, i)
            if not success:
                error_count += 1
                error_messages.append(error)
                continue

            # Check duplicate name
            with rx.session() as session:
                existing = session.exec(
                    select(Athlete).where(Athlete.name == data["name"])
                ).first()
                if existing:
                    error_count += 1
                    error_messages.append(
                        f"Row {i}: Athlete with name '{data['name']}' already exists"
                    )
                    continue

                # Create athlete
                athlete = Athlete(**data)
                session.add(athlete)
                try:
                    session.commit()
                    success_count += 1
                except Exception as e:
                    session.rollback()
                    error_count += 1
                    error_messages.append(f"Row {i}: Database error - {str(e)}")

        return success_count, error_count, error_messages

    @staticmethod
    def import_athletes_json(json_content: str) -> Tuple[int, int, List[str]]:
        """
        Import athletes from JSON string.
        Expects format: {"athletes": [{...}, ...]}
        Returns (success_count, error_count, error_messages).
        """
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            return 0, 1, [f"Invalid JSON: {str(e)}"]

        if "athletes" not in data or not isinstance(data["athletes"], list):
            return 0, 1, ["JSON must contain 'athletes' array"]

        success_count = 0
        error_count = 0
        error_messages = []

        for i, athlete_dict in enumerate(data["athletes"], start=1):
            success, athlete_data, error = ImportService.parse_athlete_row(
                athlete_dict, i
            )
            if not success:
                error_count += 1
                error_messages.append(error)
                continue

            # Check duplicate name
            with rx.session() as session:
                existing = session.exec(
                    select(Athlete).where(Athlete.name == athlete_data["name"])
                ).first()
                if existing:
                    error_count += 1
                    error_messages.append(
                        f"Item {i}: Athlete with name '{athlete_data['name']}' already exists"
                    )
                    continue

                athlete = Athlete(**athlete_data)
                session.add(athlete)
                try:
                    session.commit()
                    success_count += 1
                except Exception as e:
                    session.rollback()
                    error_count += 1
                    error_messages.append(f"Item {i}: Database error - {str(e)}")

        return success_count, error_count, error_messages

    @staticmethod
    def import_referees_csv(csv_content: str) -> Tuple[int, int, List[str]]:
        """Import referees from CSV. Similar structure to athletes."""
        # Implementation similar to import_athletes_csv but for Referee model
        # For now, placeholder
        return 0, 0, ["Referee import not yet implemented"]

    @staticmethod
    def import_teams_csv(csv_content: str) -> Tuple[int, int, List[str]]:
        """Import teams from CSV."""
        # Placeholder
        return 0, 0, ["Team import not yet implemented"]
