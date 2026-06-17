# Delta: Category Form — Kata Fields

## Purpose

Extend the operator category form (`_categories_card`) with kata-specific fields that already exist in the `TournamentCategory` model but are not exposed in UI or serialized through state. These fields MUST only appear when modality is kata.

## ADDED Requirements

### Requirement: Kata Fields Conditional Visibility

The category form MUST show 4 additional input fields when the selected modality is `KATA_INDIVIDUAL` or `KATA_TEAM`:
- `judge_panel_size` — rx.select with options `["3", "5", "7"]`
- `kata_flow_mode` — rx.select with options `["STANDARD", "INFORMAL"]`
- `scoring_type` — rx.select (see scoring rule below)
- The fields MUST be hidden when modality is kumite

#### Scenario: Kata fields visible on kata modality

- GIVEN the operator opens the category form
- WHEN modality selects "Kata Individual" or "Kata por Equipos"
- THEN 4 kata-specific fields MUST appear below the bracket_size selector
- AND they MUST be: judge_panel_size, kata_flow_mode, scoring_type

#### Scenario: Kata fields hidden on kumite modality

- GIVEN the category form is open
- WHEN modality selects "Kumite Individual" or "Kumite por Equipos"
- THEN kata-specific fields MUST NOT be rendered

### Requirement: Scoring Type Auto-Resolution

The `scoring_type` field MUST behave differently based on `kata_flow_mode`:
- When `kata_flow_mode = INFORMAL`, scoring_type MUST auto-set to `INFORMAL` and be read-only/disabled
- When `kata_flow_mode = STANDARD`, scoring_type MUST offer user-selectable options: `AVERAGE_WITH_DISCARD`, `MAJORITY_BY_JUDGE`

#### Scenario: INFORMAL locks scoring_type

- GIVEN kata_flow_mode selects "INFORMAL"
- WHEN the form renders
- THEN scoring_type MUST display "INFORMAL" as a disabled value
- AND the user MUST NOT be able to change it

#### Scenario: STANDARD offers scoring choices

- GIVEN kata_flow_mode selects "STANDARD"
- WHEN the form renders
- THEN scoring_type MUST offer selectable options: "average-with-discard" and "majority-by-judge"

### Requirement: Judge Panel Size Validation

`judge_panel_size` MUST accept only values `3`, `5`, or `7`. Any other value MUST be rejected by `_validate_form()`.

#### Scenario: Valid judge panel sizes

- GIVEN the operator sets judge_panel_size to "5"
- WHEN submitting the category form
- THEN the form MUST validate successfully

#### Scenario: Invalid judge panel size rejected

- GIVEN the operator sets judge_panel_size to "2"
- WHEN submitting the category form
- THEN the form MUST show error "Panel de jueces debe ser 3, 5 o 7"
- AND the category MUST NOT be saved

### Requirement: Kata Fields Serialization

The `_serialize_category()` method MUST include `judge_panel_size`, `kata_flow_mode`, and `scoring_type` in the returned dict. The `_validate_form()` method MUST include them in the normalized payload. The `reset_form()` MUST set defaults: `judge_panel_size = "3"`, `kata_flow_mode = "STANDARD"`, `scoring_type = "AVERAGE_WITH_DISCARD"`.

#### Scenario: Serialize kata category

- GIVEN a `TournamentCategory` row with kata modality
- WHEN `_serialize_category()` is called
- THEN the returned dict MUST contain `judge_panel_size`, `kata_flow_mode`, `scoring_type` keys with their DB values

#### Scenario: Edit kata category pre-fills kata fields

- GIVEN an existing kata category with `judge_panel_size=5`, `kata_flow_mode=INFORMAL`
- WHEN `set_form_values()` is called in edit mode
- THEN the form MUST show judge_panel_size = "5", kata_flow_mode = "INFORMAL"
