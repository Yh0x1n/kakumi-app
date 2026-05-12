"""
Import Service
Handles CSV/JSON import of athletes, referees, and teams.
"""

import datetime
import csv
import io
import json
from typing import Any, Dict, List, Optional, Tuple

import reflex as rx
from sqlalchemy.exc import SQLAlchemyError
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

    BELT_COLORS = {
        "BLANCO",
        "AMARILLO",
        "NARANJA",
        "VERDE",
        "AZUL",
        "MARRON",
        "NEGRO",
    }

    @staticmethod
    def _clean_str(value: Any) -> str:
        """Return stripped string, normalizing null/None values to empty."""
        if value is None:
            return ""
        return str(value).strip()

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
        """Validate belt rank format (Kyu/Dan or supported belt colors)."""
        if not isinstance(rank, str):
            return False
        rank = rank.strip()
        if rank.upper() in ImportService.BELT_COLORS:
            return True
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
    def parse_athlete_row(  # noqa: C901
        row: Dict, row_num: int
    ) -> Tuple[bool, Optional[Dict], str]:
        """
        Parse a single athlete row from CSV/JSON.
        Returns (success, data_dict, error_message).
        """
        errors = []
        name = ImportService._clean_str(row.get("name", ""))
        if not name or len(name) < 2 or len(name) > 255:
            errors.append("Name must be 2-255 characters")

        date_of_birth = ImportService._clean_str(row.get("date_of_birth", ""))
        if not ImportService.validate_date_iso8601(date_of_birth):
            errors.append("Invalid date_of_birth format (YYYY-MM-DD)")
        else:
            dob = datetime.datetime.strptime(date_of_birth, "%Y-%m-%d").date()
            if dob > datetime.date.today():
                errors.append("date_of_birth cannot be in the future")

        gender = ImportService._clean_str(row.get("gender", ""))
        if not ImportService.validate_gender(gender):
            errors.append("gender must be MALE or FEMALE")

        weight_str = ImportService._clean_str(row.get("weight_kg", ""))
        weight_kg = None
        if weight_str:
            try:
                weight_kg = float(weight_str)
                if not ImportService.validate_weight(weight_kg):
                    errors.append("weight_kg must be between 40.0 and 120.0")
            except ValueError:
                errors.append("weight_kg must be a number")

        belt_rank = ImportService._clean_str(row.get("belt_rank", ""))
        if belt_rank and not ImportService.validate_belt_rank(belt_rank):
            errors.append(
                "belt_rank must be 'Kyu 1-8', 'Dan 1-10', "
                "or belt colors from 'Blanco' to 'Negro'"
            )

        dojo = ImportService._clean_str(row.get("dojo", ""))
        if dojo and len(dojo) > 255:
            errors.append("dojo must be less than 255 characters")

        nationality = ImportService._clean_str(row.get("nationality", ""))
        if nationality and not ImportService.validate_country_code(nationality):
            errors.append("nationality must be ISO 3166-1 alpha-3 code")

        license_number = ImportService._clean_str(row.get("license_number", ""))

        if errors:
            return False, None, f"Row {row_num}: " + "; ".join(errors)

        data = {
            "name": name,
            "email": ImportService._clean_str(row.get("email", "")) or None,
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
        if not reader.fieldnames or not all(
            field in reader.fieldnames for field in required_fields
        ):
            return 0, 1, ["CSV missing required fields: name, date_of_birth, gender"]

        pending_rows: list[tuple[int, dict[str, Any]]] = []
        seen_names: set[str] = set()

        with rx.session() as session:
            for i, row in enumerate(reader, start=2):  # row 1 is header
                success, data, error = ImportService.parse_athlete_row(row, i)
                if not success:
                    error_count += 1
                    error_messages.append(error)
                    continue

                athlete_name = str(data["name"])
                if athlete_name in seen_names:
                    error_count += 1
                    error_messages.append(
                        f"Row {i}: Athlete with name '{athlete_name}' already exists"
                    )
                    continue

                existing = session.exec(
                    select(Athlete).where(Athlete.name == athlete_name)
                ).first()
                if existing:
                    error_count += 1
                    error_messages.append(
                        f"Row {i}: Athlete with name '{athlete_name}' already exists"
                    )
                    continue

                pending_rows.append((i, data))
                seen_names.add(athlete_name)

            try:
                for _, athlete_data in pending_rows:
                    normalized_data = dict(athlete_data)
                    normalized_data["date_of_birth"] = datetime.date.fromisoformat(
                        str(normalized_data["date_of_birth"])
                    )
                    session.add(Athlete(**normalized_data))
                if pending_rows:
                    session.commit()
                    success_count += len(pending_rows)
            except SQLAlchemyError as e:
                session.rollback()
                error_count += len(pending_rows)
                success_count = 0
                for row_num, _ in pending_rows:
                    error_messages.append(f"Row {row_num}: Database error - {str(e)}")

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

        payload = data.get("athletes")
        if not isinstance(payload, list):
            return 0, 1, ["JSON must contain 'athletes' array"]

        success_count = 0
        error_count = 0
        error_messages = []

        pending_rows: list[tuple[int, dict[str, Any]]] = []
        seen_names: set[str] = set()

        with rx.session() as session:
            for i, athlete_dict in enumerate(payload, start=1):
                success, athlete_data, error = ImportService.parse_athlete_row(
                    athlete_dict, i
                )
                if not success:
                    error_count += 1
                    error_messages.append(error)
                    continue

                athlete_name = str(athlete_data["name"])
                if ImportService._athlete_name_exists(
                    session=session,
                    athlete_name=athlete_name,
                    seen_names=seen_names,
                ):
                    error_count += 1
                    error_messages.append(
                        f"Item {i}: Athlete with name '{athlete_name}' already exists"
                    )
                    continue

                pending_rows.append((i, athlete_data))
                seen_names.add(athlete_name)

            try:
                for _, athlete_data in pending_rows:
                    normalized_data = dict(athlete_data)
                    normalized_data["date_of_birth"] = datetime.date.fromisoformat(
                        str(normalized_data["date_of_birth"])
                    )
                    session.add(Athlete(**normalized_data))
                if pending_rows:
                    session.commit()
                    success_count += len(pending_rows)
            except SQLAlchemyError as e:
                session.rollback()
                error_count += len(pending_rows)
                success_count = 0
                for item_num, _ in pending_rows:
                    error_messages.append(f"Item {item_num}: Database error - {str(e)}")

        return success_count, error_count, error_messages

    @staticmethod
    def _athlete_name_exists(
        session: Any,
        athlete_name: str,
        seen_names: set[str],
    ) -> bool:
        """Return True when athlete name is duplicated in payload or DB."""
        if athlete_name in seen_names:
            return True
        existing = session.exec(
            select(Athlete).where(Athlete.name == athlete_name)
        ).first()
        return existing is not None

    @staticmethod
    def _parse_referee_csv_row(
        row: Dict[str, str],
        row_number: int,
        valid_levels: set[str],
        valid_roles: set[str],
    ) -> Tuple[Optional[dict[str, Any]], Optional[str]]:
        """Normalize and validate a referee CSV row."""
        name = (row.get("name") or "").strip()
        license_number = (row.get("license_number") or "").strip()
        license_level = (row.get("license_level") or "NATIONAL").strip().upper()
        role = (row.get("role") or "REFEREE").strip().upper()
        is_available = (row.get("is_available") or "true").strip().lower()
        dojo = (row.get("dojo") or "").strip() or None
        email = (row.get("email") or "").strip() or None
        phone = (row.get("phone") or "").strip() or None

        row_errors = []
        if not name or len(name) < 2 or len(name) > 255:
            row_errors.append("name must be 2-255 characters")
        if not license_number or len(license_number) > 50:
            row_errors.append("license_number is required (max 50 chars)")
        if license_level not in valid_levels:
            row_errors.append("license_level must be NATIONAL or INTERNATIONAL")
        if role not in valid_roles:
            row_errors.append("role is invalid")

        available = True
        if is_available in {"true", "1", "yes", "si", "sí"}:
            available = True
        elif is_available in {"false", "0", "no"}:
            available = False
        else:
            row_errors.append("is_available must be true/false")

        if row_errors:
            return None, f"Row {row_number}: " + "; ".join(row_errors)

        return {
            "name": name,
            "license_number": license_number,
            "license_level": license_level,
            "role": role,
            "is_available": available,
            "dojo": dojo,
            "email": email,
            "phone": phone,
        }, None

    @staticmethod
    def import_referees_csv(csv_content: str) -> Tuple[int, int, List[str]]:
        """Import referees from CSV string."""
        success_count = 0
        error_count = 0
        error_messages: list[str] = []

        reader = csv.DictReader(io.StringIO(csv_content))
        required_fields = ["name", "license_number", "license_level", "role"]
        if not reader.fieldnames or not all(
            field in reader.fieldnames for field in required_fields
        ):
            return (
                0,
                1,
                [
                    "CSV missing required fields: "
                    "name, license_number, license_level, role"
                ],
            )

        valid_levels = {"NATIONAL", "INTERNATIONAL"}
        valid_roles = {"REFEREE", "JUDGE", "TABLE_OFFICIAL", "SUPERVISOR"}

        pending_rows: list[tuple[int, dict[str, Any]]] = []
        seen_licenses: set[str] = set()

        with rx.session() as session:
            for i, row in enumerate(reader, start=2):
                referee_data, row_error = ImportService._parse_referee_csv_row(
                    row=row,
                    row_number=i,
                    valid_levels=valid_levels,
                    valid_roles=valid_roles,
                )
                if row_error:
                    error_count += 1
                    error_messages.append(row_error)
                    continue

                assert referee_data is not None
                license_number = str(referee_data["license_number"])

                if license_number in seen_licenses:
                    error_count += 1
                    error_messages.append(
                        f"Row {i}: Referee with license '{license_number}' "
                        "already exists"
                    )
                    continue

                existing = session.exec(
                    select(Referee).where(Referee.license_number == license_number)
                ).first()
                if existing:
                    error_count += 1
                    error_messages.append(
                        f"Row {i}: Referee with license '{license_number}' "
                        "already exists"
                    )
                    continue

                pending_rows.append(
                    (i, referee_data)
                )
                seen_licenses.add(license_number)

            try:
                for _, referee_data in pending_rows:
                    session.add(Referee(**referee_data))
                if pending_rows:
                    session.commit()
                    success_count += len(pending_rows)
            except SQLAlchemyError as e:
                session.rollback()
                error_count += len(pending_rows)
                success_count = 0
                for row_num, _ in pending_rows:
                    error_messages.append(f"Row {row_num}: Database error - {str(e)}")

        return success_count, error_count, error_messages

    @staticmethod
    def import_referees_json(json_content: str) -> Tuple[int, int, List[str]]:
        """Import referees from JSON string ({"referees": [...]}) format."""
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            return 0, 1, [f"Invalid JSON: {str(e)}"]

        if "referees" not in data or not isinstance(data["referees"], list):
            return 0, 1, ["JSON must contain 'referees' array"]

        csv_buffer = io.StringIO()
        writer = csv.DictWriter(
            csv_buffer,
            fieldnames=[
                "name",
                "license_number",
                "license_level",
                "role",
                "is_available",
                "dojo",
                "email",
                "phone",
            ],
        )
        writer.writeheader()
        for referee in data["referees"]:
            writer.writerow(
                {
                    "name": referee.get("name", ""),
                    "license_number": referee.get("license_number", ""),
                    "license_level": referee.get("license_level", ""),
                    "role": referee.get("role", ""),
                    "is_available": referee.get("is_available", "true"),
                    "dojo": referee.get("dojo", ""),
                    "email": referee.get("email", ""),
                    "phone": referee.get("phone", ""),
                }
            )

        return ImportService.import_referees_csv(csv_buffer.getvalue())

    @staticmethod
    def import_teams_csv(csv_content: str) -> Tuple[int, int, List[str]]:
        """Import teams from CSV."""
        # Placeholder
        return 0, 0, ["Team import not yet implemented"]
