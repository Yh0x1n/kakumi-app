# Tournament Registration Specification

## Purpose

Define how tournament registration dates (`start_date`, `end_date`) are displayed, entered, parsed, and serialized throughout the tournament CRUD flow. The system MUST present dates in DD/MM/YYYY format in all UI surfaces while storing `datetime.date` objects in the database and preserving ISO 8601 keys for service-layer compatibility.

## Requirements

### Requirement: _iso_to_display Converts ISO String to DD/MM/YYYY

A helper function `_iso_to_display(iso_str: str) -> str` SHALL convert an ISO date string `"2026-06-07"` to display format `"07/06/2026"`.

The function SHALL accept only strings in `%Y-%m-%d` format. If parsing fails, the function SHALL return an empty string `""`.

#### Scenario: Standard ISO conversion

- GIVEN `iso_str = "2026-06-07"`
- WHEN `_iso_to_display(iso_str)` is called
- THEN the result MUST equal `"07/06/2026"`

#### Scenario: Invalid ISO returns empty string

- GIVEN `iso_str = "not-a-date"`
- WHEN `_iso_to_display(iso_str)` is called
- THEN the result MUST equal `""`

#### Scenario: Empty ISO returns empty string

- GIVEN `iso_str = ""`
- WHEN `_iso_to_display(iso_str)` is called
- THEN the result MUST equal `""`

### Requirement: _display_to_date Parses DD/MM/YYYY to date

A helper function `_display_to_date(display_str: str) -> datetime.date | None` SHALL parse a `"DD/MM/YYYY"` string and return a `datetime.date` object.

The function SHALL return `None` for any string that cannot be parsed as a valid date after all normalisation steps.

#### Scenario: Standard DD/MM/YYYY parsing

- GIVEN `display_str = "07/06/2026"`
- WHEN `_display_to_date(display_str)` is called
- THEN the result MUST equal `datetime.date(2026, 6, 7)`

#### Scenario: DD-MM-YYYY with dashes is accepted

- GIVEN `display_str = "07-06-2026"`
- WHEN `_display_to_date(display_str)` is called
- THEN dashes SHALL be replaced with slashes before parsing
- AND the result MUST equal `datetime.date(2026, 6, 7)`

#### Scenario: Invalid date string returns None

- GIVEN `display_str = "32/13/2026"` (invalid day/month)
- WHEN `_display_to_date(display_str)` is called
- THEN the result MUST be `None`

#### Scenario: Garbage string returns None

- GIVEN `display_str = "not-a-date"`
- WHEN `_display_to_date(display_str)` is called
- THEN the result MUST be `None`

#### Scenario: Empty string returns None

- GIVEN `display_str = ""`
- WHEN `_display_to_date(display_str)` is called
- THEN the result MUST be `None`

### Requirement: _date_to_iso Converts date to ISO String

A helper function `_date_to_iso(d: datetime.date) -> str` SHALL return `d.isoformat()` (i.e., `"YYYY-MM-DD"`).

#### Scenario: Date to ISO

- GIVEN `d = datetime.date(2026, 6, 7)`
- WHEN `_date_to_iso(d)` is called
- THEN the result MUST equal `"2026-06-07"`

### Requirement: set_form_values Converts ISO to DD/MM/YYYY

`set_form_values()` SHALL call `_iso_to_display()` on `tournament["start_date"]` and `tournament["end_date"]` before assigning to state variables `self.start_date` and `self.end_date`.

#### Scenario: Existing tournament date displayed in DD/MM/YYYY

- GIVEN `tournament["start_date"]` = `"2026-06-07"` and `tournament["end_date"]` = `"2026-06-10"`
- WHEN `set_form_values(tournament)` executes
- THEN `self.start_date` MUST equal `"07/06/2026"`
- AND `self.end_date` MUST equal `"10/06/2026"`

#### Scenario: Single-day tournament

- GIVEN `tournament["start_date"]` = `"2026-06-07"` and `tournament["end_date"]` = `"2026-06-07"`
- WHEN `set_form_values(tournament)` executes
- THEN `self.start_date` MUST equal `"07/06/2026"`
- AND `self.end_date` MUST equal `"07/06/2026"`

### Requirement: save_tournament Parses DD/MM/YYYY to date

`save_tournament()` SHALL call `_display_to_date()` on `self.start_date` and `self.end_date` instead of `strptime(..., "%Y-%m-%d")`.

The parsed `datetime.date` objects SHALL be assigned directly to the Tournament model fields (`start_date`, `end_date`).

#### Scenario: Save with valid DD/MM/YYYY

- GIVEN `self.start_date = "07/06/2026"` and `self.end_date = "10/06/2026"`
- WHEN `save_tournament()` executes the date-parsing step
- THEN the Tournament object's `start_date` MUST equal `datetime.date(2026, 6, 7)`
- AND `end_date` MUST equal `datetime.date(2026, 6, 10)`

#### Scenario: Save with dash variant

- GIVEN `self.start_date = "07-06-2026"` and `self.end_date = "10-06-2026"`
- WHEN `save_tournament()` executes the date-parsing step
- THEN dashes SHALL be replaced with slashes
- AND the Tournament object's `start_date` MUST equal `datetime.date(2026, 6, 7)`

#### Scenario: Save with invalid date triggers validation

- GIVEN `self.start_date = "not-a-date"`
- WHEN `save_tournament()` executes the date-parsing step
- THEN `_display_to_date` MUST return `None`
- AND `save_tournament()` MUST raise or handle the validation error before persisting
- AND the Tournament MUST NOT be saved to the database

### Requirement: _serialize_tournament Includes Display Keys

`_serialize_tournament()` SHALL include keys `start_date_display` and `end_date_display` with DD/MM/YYYY values alongside the existing ISO `start_date`/`end_date` keys.

Existing keys `start_date`, `end_date`, and all other keys MUST remain unchanged so that service layers continue to work without modification.

#### Scenario: Serialized dict contains both ISO and display keys

- GIVEN a Tournament with `start_date = datetime.date(2026, 6, 7)` and `end_date = datetime.date(2026, 6, 10)`
- WHEN `_serialize_tournament(tournament)` is called
- THEN the returned dict MUST contain:
  - `"start_date": "2026-06-07"` (unchanged ISO)
  - `"end_date": "2026-06-10"` (unchanged ISO)
  - `"start_date_display": "07/06/2026"` (new display)
  - `"end_date_display": "10/06/2026"` (new display)
- AND all other keys (`id`, `name`, `venue`, `status`, `tatami_count`, `created_by_id`) MUST be present and unchanged

### Requirement: Display Labels Use DD/MM/AAAA Format

Heading labels SHALL change from `"Inicio (YYYY-MM-DD)"` to `"Inicio (DD/MM/AAAA)"` and from `"Fin (YYYY-MM-DD)"` to `"Fin (DD/MM/AAAA)"`.

#### Scenario: Updated form labels in Spanish

- GIVEN the tournament form on `registries.py`
- WHEN the page renders
- THEN the start date label MUST display as `"Inicio (DD/MM/AAAA)"`
- AND the end date label MUST display as `"Fin (DD/MM/AAAA)"`

### Requirement: Tournament Table Shows DD/MM/YYYY

The tournament table in `registries.py` SHALL display `start_date_display` and `end_date_display` keys instead of the raw ISO `start_date` / `end_date` columns.

#### Scenario: Table cell shows formatted date

- GIVEN a tournament row with `start_date_display = "07/06/2026"` and `end_date_display = "10/06/2026"`
- WHEN the table renders the "Inicio" column for that row
- THEN the cell content MUST be `"07/06/2026"`
- AND the "Fin" column cell MUST be `"10/06/2026"`

### Requirement: Import-Defensive Dash Normalisation

Any user-typed or programmatic date value that contains dashes (`"-"`) SHALL have dashes replaced with slashes (`"/"`) before parse. This applies to `_display_to_date()` input and any direct state assignment path that feeds into date parsing.

#### Scenario: Dash variant in any entry point

- GIVEN a date string `"07-06-2026"`
- WHEN the string enters `_display_to_date()`
- THEN all `"-"` characters SHALL be replaced with `"/"` before parsing
- AND the result MUST equal `datetime.date(2026, 6, 7)`

### Requirement: Form Date Input Uses Select Trigger

The tournament form SHALL replace each `rx.input` date field with an `rx.select` that shows the current DD/MM/YYYY value and triggers a calendar popover on focus/click.

#### Scenario: Date field renders as select trigger

- GIVEN the tournament form edit/create mode
- WHEN the form renders for the start date
- THEN the date input MUST be an `rx.select` element
- AND its displayed value MUST be the current `self.start_date` in DD/MM/YYYY
- AND clicking/focusing the select MUST make the calendar popover visible

#### Scenario: Both dates use select triggers

- GIVEN the tournament form with both date fields
- WHEN the form renders
- THEN both `start_date` and `end_date` fields MUST be `rx.select` elements (not `rx.input`)
