"""
Import Service
Handles XLSX import of athletes, referees, and teams.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

import reflex as rx
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.referee_model import Referee
from kakumi_app.services.registry_excel_service import (
    RegistryWorkbookError,
    parse_athletes_workbook,
    parse_referees_workbook,
)
from kakumi_app.utils import BELT_RANKS


# NOTE: Team model not yet implemented
# from kakumi_app.models.team_model import Team, TeamMember


class ImportError(Exception):
    """Custom exception for import errors."""

    pass


class ImportService:
    """Service for importing registry data from XLSX workbooks."""

    BELT_COLORS = {rank.upper() for rank in BELT_RANKS} | {"MARRON"}

    @staticmethod
    def _clean_str(value: Any) -> str:
        """Return stripped string, normalizing null/None values to empty."""
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def validate_country_code(code: str) -> bool:
        """Validate ISO 3166-1 alpha-3 country code (basic check)."""
        # Simple check: 3 uppercase letters
        return isinstance(code, str) and len(code) == 3 and code.isalpha()

    @staticmethod
    def validate_gender(gender: str) -> bool:
        """Validate gender field (accepts English and Spanish values)."""
        return gender.upper() in ["MALE", "FEMALE", "MASCULINO", "FEMENINO"]

    @staticmethod
    def validate_weight(weight: float) -> bool:
        """Validate weight in kg."""
        return 40.0 <= weight <= 120.0

    @staticmethod
    def validate_age(value: Any) -> bool:
        """Validate age (0-150), accepts int or string convertible to int."""
        if isinstance(value, (int, float)):
            return 0 <= int(value) <= 150
        if isinstance(value, str):
            try:
                age = int(value.strip())
                return 0 <= age <= 150
            except ValueError:
                return False
        return False

    @staticmethod
    def validate_belt_rank(rank: str) -> bool:
        """Validate belt rank is a valid belt color (rejects Kyu/Dan numeric ranks)."""
        if not isinstance(rank, str):
            return False
        return rank.strip().upper() in ImportService.BELT_COLORS

    @staticmethod
    def parse_athlete_row(  # noqa: C901
        row: Dict, row_num: int
    ) -> Tuple[bool, Optional[Dict], str]:
        """
        Parse a single athlete row from workbook data.
        Returns (success, data_dict, error_message).
        """
        errors = []
        name = ImportService._clean_str(row.get("name", ""))
        if not name or len(name) < 2 or len(name) > 255:
            errors.append("Name must be 2-255 characters")

        age_str = ImportService._clean_str(row.get("age", ""))
        if not ImportService.validate_age(age_str):
            errors.append("age must be a number between 0 and 150")
        else:
            age = int(age_str)

        gender = ImportService._clean_str(row.get("gender", ""))
        if not ImportService.validate_gender(gender):
            errors.append(
                "gender must be MALE/FEMALE or MASCULINO/FEMENINO"
            )

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
                "belt_rank must be a valid belt color: "
                "Blanco, Celeste, Amarillo, Naranja, Verde, "
                "Azul, Morado, Marrón, or Negro"
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

        # Normalize gender: Spanish → English for DB storage
        raw_gender = gender.upper()
        if raw_gender == "MASCULINO":
            raw_gender = "MALE"
        elif raw_gender == "FEMENINO":
            raw_gender = "FEMALE"

        data = {
            "name": name,
            "email": ImportService._clean_str(row.get("email", "")) or None,
            "age": age,
            "gender": raw_gender,
            "weight_kg": weight_kg,
            "belt_rank": belt_rank or None,
            "dojo": dojo or None,
            "nationality": nationality or None,
            "license_number": license_number or None,
        }
        return True, data, ""

    @staticmethod
    def _import_athlete_rows(rows: Sequence[Dict[str, Any]]) -> Tuple[int, int, List[str]]:
        """
        Import athletes from normalized workbook rows.
        Returns (success_count, error_count, error_messages).
        """
        success_count = 0
        error_count = 0
        error_messages = []

        pending_rows: list[tuple[int, dict[str, Any]]] = []
        seen_names: set[str] = set()

        with rx.session() as session:
            for i, row in enumerate(rows, start=2):
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
                    normalized_data["age"] = int(normalized_data["age"])
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
    def import_athletes_xlsx(workbook_bytes: bytes) -> Tuple[int, int, List[str]]:
        """
        Import athletes from XLSX workbook bytes.
        Returns (success_count, error_count, error_messages).
        """
        try:
            rows = parse_athletes_workbook(workbook_bytes)
        except RegistryWorkbookError as exc:
            return 0, 1, [str(exc)]
        return ImportService._import_athlete_rows(rows)

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
    def _normalize_license_level(level: str) -> str:
        """Convert Spanish license_level to DB English."""
        normalized = (level or "").strip().upper()
        if normalized == "NACIONAL":
            return "NATIONAL"
        if normalized == "INTERNACIONAL":
            return "INTERNATIONAL"
        return normalized

    @staticmethod
    def _normalize_role(role: str) -> str:
        """Convert Spanish role to DB English."""
        normalized = (role or "").strip().upper()
        if normalized == "JUEZ":
            return "JUDGE"
        if normalized == "OFICIAL DE MESA":
            return "TABLE_OFFICIAL"
        if normalized == "SUPERVISOR (KANSA)":
            return "SUPERVISOR"
        return normalized

    @staticmethod
    def _parse_referee_row(
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
            "license_level": ImportService._normalize_license_level(license_level),
            "role": ImportService._normalize_role(role),
            "is_available": available,
            "dojo": dojo,
            "email": email,
            "phone": phone,
        }, None

    @staticmethod
    def _import_referee_rows(rows: Sequence[Dict[str, str]]) -> Tuple[int, int, List[str]]:
        """Import referees from normalized workbook rows."""
        success_count = 0
        error_count = 0
        error_messages: list[str] = []

        valid_levels = {"NATIONAL", "INTERNATIONAL", "NACIONAL", "INTERNACIONAL"}
        valid_roles = {
            "REFEREE", "JUDGE", "TABLE_OFFICIAL", "SUPERVISOR",
            "JUEZ", "OFICIAL DE MESA", "SUPERVISOR (KANSA)",
        }

        pending_rows: list[tuple[int, dict[str, Any]]] = []
        seen_licenses: set[str] = set()

        with rx.session() as session:
            for i, row in enumerate(rows, start=2):
                referee_data, row_error = ImportService._parse_referee_row(
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
    def import_referees_xlsx(workbook_bytes: bytes) -> Tuple[int, int, List[str]]:
        """Import referees from XLSX workbook bytes."""
        try:
            rows = parse_referees_workbook(workbook_bytes)
        except RegistryWorkbookError as exc:
            return 0, 1, [str(exc)]
        return ImportService._import_referee_rows(rows)

    @staticmethod
    def import_teams_csv(csv_content: str) -> Tuple[int, int, List[str]]:
        """Import teams from CSV."""
        # Placeholder
        return 0, 0, ["Team import not yet implemented"]
