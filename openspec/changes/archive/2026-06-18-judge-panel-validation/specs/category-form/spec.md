# Delta for Category Form

## ADDED Requirements

### Requirement: Tournament Status Restriction on Category CRUD

The `TournamentCategoryState` MUST restrict category create and edit operations based on tournament status. The category form MUST NOT open and category save MUST be blocked when the selected tournament's status is not one of the allowed pre-competition statuses.

The `TournamentCategoryState` MUST include a `_current_tournament_status: str` state variable that is populated from `tournament.status` in `set_tournament_context()` and cleared to `""` when the tournament is not found.

#### Guard: `set_form_values()` (both create and edit paths)

When `set_form_values()` is called, if `self._current_tournament_status` is not one of:

- `TournamentStatus.PLANIFICADO.value`
- `TournamentStatus.INSCRIPCION.value`
- `TournamentStatus.VERIFICACION.value`

THEN the method MUST:

- Set `self.error_message` to `"Solo se pueden gestionar categorías en torneos no iniciados"`
- Return early without opening the form (no `_set_form_open`, no field population)

#### Guard: `save_category()` (create and update)

When `save_category()` is called, if `self._current_tournament_status` is not one of:

- `TournamentStatus.PLANIFICADO.value`
- `TournamentStatus.INSCRIPCION.value`
- `TournamentStatus.VERIFICACION.value`

THEN the method MUST:

- Set `self.error_message` to `"Solo se pueden crear categorías en torneos no iniciados"`
- Return `rx.toast.error(self.error_message)` immediately without persisting any data

#### Scenario: Form blocked on EN_CURSO tournament

- GIVEN a tournament with status `EN_CURSO`
- AND the operator attempts to open the category form (create or edit)
- WHEN `set_form_values()` is called
- THEN `self.error_message` MUST be set
- AND the form MUST NOT open
- AND the error message MUST read `"Solo se pueden gestionar categorías en torneos no iniciados"`

#### Scenario: Save blocked on FINALIZADO tournament

- GIVEN a tournament with status `FINALIZADO`
- AND the operator somehow bypasses the form guard (e.g., programmatic call)
- WHEN `save_category()` is called
- THEN the method MUST return `rx.toast.error(...)` immediately
- AND no category data MUST be persisted
- AND the error message MUST read `"Solo se pueden crear categorías en torneos no iniciados"`

#### Scenario: Form opens on PLANIFICADO tournament

- GIVEN a tournament with status `PLANIFICADO`
- WHEN `set_form_values()` is called with a category or `None`
- THEN the form MUST open normally
- AND `self.error_message` MUST remain empty

#### Scenario: Form opens on INSCRIPCION tournament

- GIVEN a tournament with status `INSCRIPCION`
- WHEN `set_form_values()` is called
- THEN the form MUST open normally (allowed status)

#### Scenario: Form opens on VERIFICACION tournament

- GIVEN a tournament with status `VERIFICACION`
- WHEN `set_form_values()` is called
- THEN the form MUST open normally (allowed status)

#### Scenario: Save allowed on INSCRIPCION tournament

- GIVEN a tournament with status `INSCRIPCION`
- AND valid form data
- WHEN `save_category()` is called
- THEN the category MUST be persisted normally

#### Scenario: Status variable lifecycle

- GIVEN `set_tournament_context()` is called with a valid tournament
- THEN `_current_tournament_status` MUST equal `tournament.status`
- WHEN the tournament is not found
- THEN `_current_tournament_status` MUST be reset to `""`

## REMOVED Requirements

*(None. The judge panel warning feature was reverted before it reached canonical specs — the archived `judge-panel-validation-warning` change was blocked from syncing. No canonical requirements are removed.)*
