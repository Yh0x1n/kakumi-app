"""Unit tests for registry Excel workbook contract."""

from __future__ import annotations

from io import BytesIO

import openpyxl
import pytest

from kakumi_app.services.registry_excel_service import (
    ATHLETE_WORKBOOK_ADAPTER,
    REFEREE_WORKBOOK_ADAPTER,
    RegistryWorkbookError,
    build_athletes_workbook,
    build_referees_workbook,
    parse_athletes_workbook,
    parse_referees_workbook,
)


def test_build_athlete_workbook_uses_spanish_headers() -> None:
    workbook_bytes = build_athletes_workbook(
        [
            {
                "name": "Ana Gómez",
                "email": "ana@test.dev",
                "age": 26,
                "gender": "FEMALE",
                "weight_kg": 55.5,
                "belt_rank": "Negro",
                "dojo": "Dojo Sur",
                "nationality": "ARG",
                "license_number": "ATH-1",
            }
        ]
    )

    workbook = openpyxl.load_workbook(filename=BytesIO(workbook_bytes))
    sheet = workbook[ATHLETE_WORKBOOK_ADAPTER.sheet_name]

    assert [cell.value for cell in sheet[1]] == list(ATHLETE_WORKBOOK_ADAPTER.headers)
    assert [cell.value for cell in sheet[2]][0] == "Ana Gómez"
    assert [cell.value for cell in sheet[2]][2] == "26"


def test_parse_referee_workbook_normalizes_rows() -> None:
    workbook_bytes = build_referees_workbook(
        [
            {
                "name": "Ref Uno",
                "license_number": "REF-10",
                "license_level": "NATIONAL",
                "role": "REFEREE",
                "is_available": "true",
                "dojo": "Dojo Norte",
                "email": "ref@test.dev",
                "phone": "123",
            }
        ]
    )

    assert parse_referees_workbook(workbook_bytes) == [
        {
            "name": "Ref Uno",
            "license_number": "REF-10",
            "license_level": "NACIONAL",
            "role": "REFEREE",
            "is_available": "true",
            "dojo": "Dojo Norte",
            "email": "ref@test.dev",
            "phone": "123",
        }
    ]


def test_parse_athlete_workbook_requires_expected_headers() -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = ATHLETE_WORKBOOK_ADAPTER.sheet_name
    sheet.append(["Nombre", "Correo electrónico"])

    buffer = BytesIO()
    workbook.save(buffer)

    with pytest.raises(RegistryWorkbookError, match="XLSX missing required headers"):
        parse_athletes_workbook(buffer.getvalue())


def test_parse_athlete_workbook_rejects_legacy_xls_payload() -> None:
    legacy_xls_bytes = bytes.fromhex("D0CF11E0A1B11AE1")

    with pytest.raises(RegistryWorkbookError, match="Invalid XLSX workbook"):
        parse_athletes_workbook(legacy_xls_bytes)


def test_parse_empty_workbook_skips_blank_rows() -> None:
    workbook_bytes = build_referees_workbook(
        [
            {
                "name": "",
                "license_number": "",
                "license_level": "",
                "role": "",
                "is_available": "",
            }
        ]
    )

    assert parse_referees_workbook(workbook_bytes) == []


def test_referee_headers_stay_human_readable_spanish() -> None:
    assert list(REFEREE_WORKBOOK_ADAPTER.headers) == [
        "Nombre",
        "Número de licencia",
        "Nivel de licencia",
        "Rol",
        "Disponible",
        "Dojo",
        "Correo electrónico",
        "Teléfono",
    ]
