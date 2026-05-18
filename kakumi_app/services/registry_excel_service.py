"""Shared Excel workbook contract for registry import/export."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Callable, Mapping, Sequence

from openpyxl import Workbook, load_workbook


class RegistryWorkbookError(ValueError):
    """Raised when a registry workbook does not match expected contract."""


# ── Enum translation maps (DB → Español para export) ────────────────────

GENDER_TRANSLATION: dict[str, str] = {
    "MALE": "MASCULINO",
    "FEMALE": "FEMENINO",
}

LICENSE_LEVEL_TRANSLATION: dict[str, str] = {
    "NATIONAL": "NACIONAL",
    "INTERNATIONAL": "INTERNACIONAL",
}

ROLE_TRANSLATION: dict[str, str] = {
    "REFEREE": "REFEREE",
    "JUDGE": "JUEZ",
    "TABLE_OFFICIAL": "OFICIAL DE MESA",
    "SUPERVISOR": "SUPERVISOR (KANSA)",
}

# Reverse maps (Español → DB para import)
GENDER_REVERSE: dict[str, str] = {v: k for k, v in GENDER_TRANSLATION.items()}
LICENSE_LEVEL_REVERSE: dict[str, str] = {v: k for k, v in LICENSE_LEVEL_TRANSLATION.items()}
ROLE_REVERSE: dict[str, str] = {v: k for k, v in ROLE_TRANSLATION.items()}


def _serialize_cell_value(value: Any) -> str:
    """Convert Python values to stable workbook cell strings."""
    if value is None:
        return ""
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return str(value).strip()


def _normalize_cell_value(value: Any) -> str:
    """Normalize openpyxl cell values to string values expected by services."""
    if value is None:
        return ""
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


CellSerializer = Callable[[Mapping[str, Any]], str]


@dataclass(frozen=True)
class RegistryColumn:
    """Workbook column contract for a registry entity."""

    field_name: str
    header: str
    required: bool = False
    serializer: CellSerializer | None = None

    def serialize(self, row: Mapping[str, Any]) -> str:
        """Return export-safe string for this column and row."""
        if self.serializer is not None:
            return self.serializer(row)
        return _serialize_cell_value(row.get(self.field_name))


@dataclass(frozen=True)
class RegistryWorkbookAdapter:
    """Adapter describing one registry workbook schema."""

    sheet_name: str
    columns: tuple[RegistryColumn, ...]

    @property
    def headers(self) -> tuple[str, ...]:
        """Return ordered workbook headers."""
        return tuple(column.header for column in self.columns)


def _text_serializer(field_name: str) -> CellSerializer:
    """Create default text serializer for a field name."""

    def _serializer(row: Mapping[str, Any]) -> str:
        return _serialize_cell_value(row.get(field_name))

    return _serializer


def _translation_serializer(
    translation_map: dict[str, str],
    field_name: str,
) -> CellSerializer:
    """Create a serializer that translates DB values to Español for export."""

    def _serializer(row: Mapping[str, Any]) -> str:
        raw = row.get(field_name)
        return translation_map.get(raw, _serialize_cell_value(raw))

    return _serializer


ATHLETE_WORKBOOK_ADAPTER = RegistryWorkbookAdapter(
    sheet_name="Atletas",
    columns=(
        RegistryColumn("name", "Nombre", required=True),
        RegistryColumn("email", "Correo electrónico"),
        RegistryColumn("date_of_birth", "Fecha de nacimiento", required=True),
        RegistryColumn(
            "gender", "Género", required=True,
            serializer=_translation_serializer(GENDER_TRANSLATION, "gender"),
        ),
        RegistryColumn("weight_kg", "Peso (kg)"),
        RegistryColumn("belt_rank", "Grado"),
        RegistryColumn("dojo", "Dojo"),
        RegistryColumn("nationality", "Nacionalidad (ISO3)"),
        RegistryColumn("license_number", "Número de licencia"),
    ),
)


REFEREE_WORKBOOK_ADAPTER = RegistryWorkbookAdapter(
    sheet_name="Árbitros",
    columns=(
        RegistryColumn("name", "Nombre", required=True),
        RegistryColumn("license_number", "Número de licencia", required=True),
        RegistryColumn(
            "license_level", "Nivel de licencia", required=True,
            serializer=_translation_serializer(LICENSE_LEVEL_TRANSLATION, "license_level"),
        ),
        RegistryColumn(
            "role", "Rol", required=True,
            serializer=_translation_serializer(ROLE_TRANSLATION, "role"),
        ),
        RegistryColumn("is_available", "Disponible", serializer=_text_serializer("is_available")),
        RegistryColumn("dojo", "Dojo"),
        RegistryColumn("email", "Correo electrónico"),
        RegistryColumn("phone", "Teléfono"),
    ),
)


def build_registry_workbook(
    adapter: RegistryWorkbookAdapter,
    rows: Sequence[Mapping[str, Any]],
) -> bytes:
    """Build an .xlsx workbook for a registry adapter."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = adapter.sheet_name
    worksheet.append(list(adapter.headers))

    for row in rows:
        worksheet.append([column.serialize(row) for column in adapter.columns])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def parse_registry_workbook(
    workbook_bytes: bytes,
    adapter: RegistryWorkbookAdapter,
) -> list[dict[str, str]]:
    """Parse an .xlsx workbook into canonical service row dictionaries."""
    if not workbook_bytes:
        raise RegistryWorkbookError("XLSX workbook is empty")

    try:
        workbook = load_workbook(BytesIO(workbook_bytes), data_only=True)
    except Exception as exc:  # pragma: no cover - openpyxl exception details vary
        raise RegistryWorkbookError("Invalid XLSX workbook") from exc

    worksheet = (
        workbook[adapter.sheet_name]
        if adapter.sheet_name in workbook.sheetnames
        else workbook.active
    )

    header_row = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
    headers = [_normalize_cell_value(value) for value in header_row]
    if not any(headers):
        raise RegistryWorkbookError("XLSX workbook is missing headers")

    header_to_column = {column.header: column for column in adapter.columns}
    missing_headers = [
        column.header
        for column in adapter.columns
        if column.required and column.header not in headers
    ]
    if missing_headers:
        joined = ", ".join(missing_headers)
        raise RegistryWorkbookError(f"XLSX missing required headers: {joined}")

    parsed_rows: list[dict[str, str]] = []
    for row_values in worksheet.iter_rows(min_row=2, values_only=True):
        row_dict: dict[str, str] = {}
        for index, header in enumerate(headers):
            column = header_to_column.get(header)
            if column is None:
                continue
            cell_value = row_values[index] if index < len(row_values) else None
            row_dict[column.field_name] = _normalize_cell_value(cell_value)

        if any(value for value in row_dict.values()):
            parsed_rows.append(row_dict)

    return parsed_rows


def build_athletes_workbook(rows: Sequence[Mapping[str, Any]]) -> bytes:
    """Build athlete registry workbook bytes."""
    return build_registry_workbook(ATHLETE_WORKBOOK_ADAPTER, rows)


def parse_athletes_workbook(workbook_bytes: bytes) -> list[dict[str, str]]:
    """Parse athlete workbook bytes into import rows."""
    return parse_registry_workbook(workbook_bytes, ATHLETE_WORKBOOK_ADAPTER)


def build_referees_workbook(rows: Sequence[Mapping[str, Any]]) -> bytes:
    """Build referee registry workbook bytes."""
    return build_registry_workbook(REFEREE_WORKBOOK_ADAPTER, rows)


def parse_referees_workbook(workbook_bytes: bytes) -> list[dict[str, str]]:
    """Parse referee workbook bytes into import rows."""
    return parse_registry_workbook(workbook_bytes, REFEREE_WORKBOOK_ADAPTER)
