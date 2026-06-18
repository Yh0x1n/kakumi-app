# Apply Progress — judge-panel-validation

## Changes Applied

### REVERT judge panel warning feature

- `kakumi_app/states/tournament_category_state.py`:
  - `from sqlmodel import func` → `select` only
  - Removed `from kakumi_app.models.referee_model import Referee`
  - Removed `_referee_count: int = 0` state var
  - Removed `judge_panel_warning` @rx.var method
  - Removed `_load_referee_count()` method
  - `set_judge_panel_size()`: removed `self._load_referee_count()` call
  - `set_form_values()`: removed both `self._load_referee_count()` calls
  - KEPT `_current_tournament_status`, `TournamentStatus` import, and its population in `set_tournament_context()`

- `kakumi_app/pages/tournament.py`:
  - Removed `rx.cond(state.judge_panel_warning != "", ...)` block from kata form section

- `tests/test_tournament_category_state.py`:
  - Removed `from kakumi_app.models.referee_model import Referee`
  - Removed all 9 judge panel warning test functions

### ADD tournament status guard

- `kakumi_app/states/tournament_category_state.py`:
  - `save_category()`: Guard prevents creating categories when `_current_tournament_status` is not PLANIFICADO, INSCRIPCION, or VERIFICACION
  - `set_form_values()`: Same guard prevents opening the form for editing/creating on locked tournaments

### Deviation from spec

- Used `return rx.toast.error(...)` instead of `yield rx.toast.error(...); return None` in `save_category()`. Using `yield` would transform the function into an async generator, breaking `await save_category.fn(state)` in existing tests. Both patterns produce the same UX (toast + early exit).

## Test Results

- `tests/test_tournament_category_state.py`: 13 passed, 0 failed
- `tests/test_kata_match_state.py`: 37 passed, 0 failed
