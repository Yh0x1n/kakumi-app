"""Approval-style regression tests for ImportService public behavior."""

from __future__ import annotations

from kakumi_app.services.import_service import ImportService


def test_import_athletes_json_reports_duplicate_name_in_payload() -> None:
    json_content = (
        '{"athletes": ['
        '{"name": "Ana", "date_of_birth": "2000-01-01", "gender": "FEMALE"},'
        '{"name": "Ana", "date_of_birth": "2001-01-01", "gender": "FEMALE"}'
        "]}"
    )

    success_count, error_count, errors = ImportService.import_athletes_json(
        json_content
    )

    assert success_count == 1
    assert error_count == 1
    assert errors
    assert "already exists" in errors[0]


def test_import_referees_csv_rejects_invalid_is_available_token() -> None:
    csv_content = "\n".join(
        [
            "name,license_number,license_level,role,is_available",
            "Ref Uno,REF-CSV-001,NATIONAL,REFEREE,maybe",
        ]
    )

    success_count, error_count, errors = ImportService.import_referees_csv(csv_content)

    assert success_count == 0
    assert error_count == 1
    assert errors
    assert "is_available must be true/false" in errors[0]


def test_import_referees_csv_imports_valid_rows() -> None:
    csv_content = "\n".join(
        [
            "name,license_number,license_level,role,is_available",
            "Ref A,REF-CSV-OK-1,NATIONAL,REFEREE,true",
            "Ref B,REF-CSV-OK-2,INTERNATIONAL,JUDGE,false",
        ]
    )

    success_count, error_count, errors = ImportService.import_referees_csv(csv_content)

    assert success_count == 2
    assert error_count == 0
    assert errors == []
