"""Regression tests for registry XLSX service behavior."""

from __future__ import annotations

from kakumi_app.services.export_service import ExportService
from kakumi_app.services.import_service import ImportService
from kakumi_app.services.registry_excel_service import (
    build_athletes_workbook,
    build_referees_workbook,
)


def test_import_athletes_xlsx_reports_duplicate_name_in_payload() -> None:
    workbook_bytes = build_athletes_workbook(
        [
            {"name": "Ana", "date_of_birth": "2000-01-01", "gender": "FEMENINO"},
            {"name": "Ana", "date_of_birth": "2001-01-01", "gender": "FEMENINO"},
        ]
    )

    success_count, error_count, errors = ImportService.import_athletes_xlsx(
        workbook_bytes
    )

    assert success_count == 1
    assert error_count == 1
    assert errors
    assert "already exists" in errors[0]


def test_import_referees_xlsx_rejects_invalid_is_available_token() -> None:
    workbook_bytes = build_referees_workbook(
        [
            {
                "name": "Ref Uno",
                "license_number": "REF-CSV-001",
                "license_level": "NACIONAL",
                "role": "REFEREE",
                "is_available": "maybe",
            }
        ]
    )

    success_count, error_count, errors = ImportService.import_referees_xlsx(
        workbook_bytes
    )

    assert success_count == 0
    assert error_count == 1
    assert errors
    assert "is_available must be true/false" in errors[0]


def test_import_referees_xlsx_imports_valid_rows() -> None:
    workbook_bytes = build_referees_workbook(
        [
            {
                "name": "Ref A",
                "license_number": "REF-CSV-OK-1",
                "license_level": "NACIONAL",
                "role": "REFEREE",
                "is_available": "true",
            },
            {
                "name": "Ref B",
                "license_number": "REF-CSV-OK-2",
                "license_level": "INTERNACIONAL",
                "role": "JUEZ",
                "is_available": "false",
            },
        ]
    )

    success_count, error_count, errors = ImportService.import_referees_xlsx(
        workbook_bytes
    )

    assert success_count == 2
    assert error_count == 0
    assert errors == []


def test_registry_services_do_not_expose_registry_json_entrypoints() -> None:
    missing_entrypoints = (
        (ImportService, "import_athletes_json"),
        (ImportService, "import_referees_json"),
        (ExportService, "export_athletes_json"),
        (ExportService, "export_referees_json"),
    )

    for service, entrypoint in missing_entrypoints:
        assert hasattr(service, entrypoint) is False
