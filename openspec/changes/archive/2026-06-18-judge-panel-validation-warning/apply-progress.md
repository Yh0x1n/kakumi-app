# Apply Progress — Judge Panel Validation Warning

## Status

All 14 tasks implemented. 22/22 tests pass (13 existing + 9 new). No regressions in full suite (914 pass, 3 pre-existing failures in `test_dashboard_state.py` unrelated to this change).

## Completed Tasks

### Implementation (Tasks 1–5)

- [x] **Task 1** — `kakumi_app/states/tournament_category_state.py`
  - Added `func` to imports: `from sqlmodel import func, select`
  - Added `Referee` import from `kakumi_app.models.referee_model`
  - Added state variable `_referee_count: int = 0`
  - Added `_load_referee_count()` method querying `select(func.count(Referee.id))`

- [x] **Task 2** — Added `@rx.var judge_panel_warning(self) -> str` after `has_selected_tournament_context`
  - Normalizes modality, checks KATA_INDIVIDUAL/KATA_TEAM, compares panel_size to_referee_count
  - Returns `"Jueces disponibles: X. Panel requiere: Y."` or `""`

- [x] **Task 3** — Wired `set_judge_panel_size()` to call `self._load_referee_count()` after setting value

- [x] **Task 4** — Wired `set_form_values()`:
  - Edit path: `self._load_referee_count()` before `return`
  - Create path: `self._load_referee_count()` after `self.reset_form()`

- [x] **Task 5** — `kakumi_app/pages/tournament.py`: Added `rx.cond` with `rx.text` after `judge_panel_size` select in kata fields block
  - `color_scheme="amber"`, `font_size="sm"`

### Tests (Tasks 6–14)

All tests added to `tests/test_tournament_category_state.py`:

- [x] **Task 6** — `test_judge_panel_warning_initial_referee_count_is_zero`
- [x] **Task 7** — `test_judge_panel_warning_load_referee_count_from_db`
- [x] **Task 8** — `test_judge_panel_warning_on_create_when_panel_exceeds_referees`
- [x] **Task 9** — `test_judge_panel_warning_on_edit_when_panel_exceeds_referees`
- [x] **Task 10** — `test_judge_panel_warning_no_warning_when_referees_sufficient`
- [x] **Task 11** — `test_judge_panel_warning_dropping_panel_removes_warning`
- [x] **Task 12** — `test_judge_panel_warning_no_warning_for_kumite`
- [x] **Task 13** — `test_judge_panel_warning_save_succeeds_with_warning_active`
- [x] **Task 14** — `test_judge_panel_warning_zero_referees_shows_warning`

## Files Changed

| File | Lines | Change |
|------|-------|--------|
| `kakumi_app/states/tournament_category_state.py` | +27 | Imports, state var, method, @rx.var, wiring |
| `kakumi_app/pages/tournament.py` | +8 | rx.cond + rx.text in kata fields block |
| `tests/test_tournament_category_state.py` | +126 | 9 new async test functions |
| `openspec/changes/judge-panel-validation-warning/tasks.md` | 14 checkboxes | Marked all tasks `[x]` |

## Deviations from Design

- **Test 11 (dropping panel)**: Design specified 2 Referees with panel=7→warning, panel=3→no warning. However 3 > 2 is mathematically true, so panel=3 would still show warning with 2 referees. Corrected to use **5 referees** (panel=7→5>7→warning, panel=3→3<5→no warning). The scenario intent (dropping panel removes warning) is preserved.
- All other tests match the design exactly.

## Test Results

```text
$ python -m pytest tests/test_tournament_category_state.py -v
→ 22 passed (13 existing + 9 new)

$ python -m pytest tests/ -v
→ 914 passed, 3 failed (pre-existing Redis/auth-state issues in test_dashboard_state.py)
```

## Verification Evidence

- Warning renders on create path when panel > referees
- Warning renders on edit path when pre-filled panel > referees
- Warning updates reactively on panel_size dropdown change (DB query per change)
- No warning for kumite modality
- No warning when referees are sufficient
- Dropping panel size removes warning when new size ≤ referee count
- Save succeeds with warning active
- Warning for all panel sizes when zero referees exist
- Warning text: "Jueces disponibles: {count}. Panel requiere: {size}."
- Color: amber, font_size: sm (small)

## Remaining Tasks

None. All tasks complete. Ready for verify.
