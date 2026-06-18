# Delta for Category Form

## ADDED Requirements

### Requirement: Judge Panel Available Referee Warning

The system MUST display an advisory warning below the `judge_panel_size` select when the selected panel size exceeds the total number of `Referee` records in the database (all roles, no filter). The warning MUST:

- Count ALL `Referee` rows via a `COUNT(*)` query on the `referees` table
- Re-evaluate the count every time `judge_panel_size` changes via `on_change`
- Render warning text only when the condition is true
- Render nothing (empty string, no DOM element) when the condition is false or when modality is kumite
- NOT block form submission — the operator MAY save the category regardless of the warning state
- Display the warning in Spanish: `"Jueces disponibles: {count}. Panel requiere: {size}."`
- Display the warning inline, immediately after the `judge_panel_size` select, within the kata-fields block
- Use a warning color (e.g. amber/orange, `color_scheme="amber"` or equivalent) and small text size

The warning is purely advisory. Its presence or absence does not affect `_validate_form()`, `save_category()`, or any other serialization or persistence logic.

#### Scenario: Warning visible on create when panel size exceeds referee count

- GIVEN the operator opens the create category form
- AND the modality is set to "Kata Individual" or "Kata por Equipos"
- AND there are exactly 2 `Referee` records in the database
- WHEN the operator selects `judge_panel_size = "7"`
- THEN the form MUST display `"Jueces disponibles: 2. Panel requiere: 7."` below the panel size select
- AND the text MUST use a warning color
- AND the save button MUST remain enabled

#### Scenario: Warning visible on edit under same conditions

- GIVEN the operator opens the edit category form for an existing kata category
- AND the pre-filled `judge_panel_size` is `"5"`
- AND there are exactly 2 `Referee` records in the database
- WHEN the form renders in edit mode
- THEN the warning `"Jueces disponibles: 2. Panel requiere: 5."` MUST be visible below the panel size select

#### Scenario: No warning when referees are sufficient

- GIVEN the operator is on the create category form for kata modality
- AND there are 8 `Referee` records in the database
- WHEN the operator selects `judge_panel_size = "5"`
- THEN no warning text MUST appear below the panel size select

#### Scenario: Dropping panel size removes warning

- GIVEN the operator is on the create category form for kata modality
- AND there are 2 `Referee` records in the database
- AND `judge_panel_size` is currently set to `"7"` with the warning visible
- WHEN the operator changes `judge_panel_size` to `"3"`
- THEN the warning MUST disappear (the condition `3 > 2` is false)

#### Scenario: No warning for kumite modality

- GIVEN the operator opens the create category form
- AND the modality is set to "Kumite Individual" or "Kumite por Equipos"
- WHEN kata-specific fields are hidden
- THEN the warning MUST NOT be rendered anywhere in the form
- AND the `_referee_count` MUST NOT be queried on panel size change (no kata fields are rendered)

#### Scenario: Save succeeds with warning active

- GIVEN the operator is on the create category form for kata modality
- AND there are 2 `Referee` records in the database
- AND `judge_panel_size = "7"` with the warning visible
- WHEN the operator clicks "Guardar categoría"
- THEN the category MUST be created successfully
- AND the system MUST NOT prevent the save operation

#### Scenario: Warning triggers DB query on every panel size change

- GIVEN the operator is on the create category form for kata modality
- AND there are 2 `Referee` records in the database
- WHEN the operator selects `judge_panel_size = "5"`
- THEN a `COUNT(*)` query against the `referees` table MUST execute
- AND if the count (2) < panel size (5), the warning MUST appear
- WHEN the operator subsequently selects `judge_panel_size = "3"`
- THEN another `COUNT(*)` query MUST execute
- AND the warning MUST reflect the updated comparison

#### Scenario: Zero referees shows warning for any non-zero panel size

- GIVEN there are 0 `Referee` records in the database
- AND the operator is on the create category form for kata modality
- WHEN the operator selects any `judge_panel_size` value (`"3"`, `"5"`, or `"7"`)
- THEN the warning MUST display: `"Jueces disponibles: 0. Panel requiere: {n}."`
- AND the save MUST still succeed

### Requirement: Referee Count State Variable

The `TournamentCategoryState` MUST contain a `_referee_count: int` state variable defaulting to `0`. This variable is populated by `_load_referee_count()` which executes `SELECT COUNT(*) FROM referees` inside a `rx.session()` context. The variable is read by the `judge_panel_warning` computed var to build the warning string.

#### Scenario: Referee count initializes to zero

- GIVEN a fresh `TournamentCategoryState` instance
- THEN `_referee_count` MUST equal `0`

#### Scenario: Load referee count queries from database

- GIVEN the database has 5 `Referee` rows
- WHEN `_load_referee_count()` is called
- THEN `_referee_count` MUST equal `5`
