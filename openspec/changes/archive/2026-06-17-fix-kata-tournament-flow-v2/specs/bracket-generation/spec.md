# Delta: Bracket Generation — INFORMAL Guard

## Purpose

Prevent `_generate_brackets_for_tournament()` from creating `Match` records for categories whose `kata_flow_mode` equals `INFORMAL`. INFORMAL categories use the `KataInformalPerformance` model for operations-driven scoring and MUST NOT produce bracket structures.

## MODIFIED Requirements

### Requirement: Bracket Generation Skips INFORMAL Categories

The system MUST generate brackets (Match records) only for categories whose `kata_flow_mode` is `STANDARD`. Categories with `kata_flow_mode = INFORMAL` MUST be skipped during bracket generation in `_generate_brackets_for_tournament()`.
(Previously: all categories with valid competition_system generated brackets regardless of kata_flow_mode)

#### Scenario: INFORMAL category skipped during bracket generation

- GIVEN a tournament with 2 categories: one STANDARD kata, one INFORMAL kata
- WHEN `transition_to(EN_CURSO)` is called
- THEN STANDARD category MUST have Match records created
- AND INFORMAL category MUST have zero Match records in the database

#### Scenario: STANDARD category unaffected

- GIVEN a tournament with a STANDARD kata category using ELIMINATION system
- WHEN bracket generation runs
- THEN it MUST create Match records as before with all existing rules
- AND the INFORMAL guard MUST NOT alter STANDARD behavior

#### Scenario: Mixed tournament skips only INFORMAL

- GIVEN a tournament with 3 categories: STANDARD kata, INFORMAL kata, STANDARD kumite
- WHEN bracket generation runs
- THEN only the INFORMAL kata category MUST be skipped
- AND both STANDARD categories MUST receive their normal Match records

#### Scenario: No INFORMAL categories — no change

- GIVEN a tournament where zero categories have `kata_flow_mode = INFORMAL`
- WHEN bracket generation runs
- THEN ALL categories with valid competition_system MUST generate brackets as before
- AND the guard MUST produce zero behavioral change

### Requirement: Validation for INFORMAL Categories on Transition

The `_validate_finalizado()` method already distinguishes INFORMAL categories by checking `kata_flow_mode`. No additional validation changes needed.

## REMOVED Requirements

(This section intentionally blank — no requirements removed.)
