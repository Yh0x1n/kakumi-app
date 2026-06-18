# Tasks — Judge Panel Validation Warning on Category Form

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~130–150 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | pending |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

## Summary

Add a reactive advisory warning below the `judge_panel_size` select on the
category create/edit form when selected panel size exceeds total `Referee`
records in the DB. Pure advisory — does not block saving.

### Files touched

| File | Change |
|------|--------|
| `kakumi_app/states/tournament_category_state.py` | +20 lines |
| `kakumi_app/pages/tournament.py` | +8 lines |
| `tests/test_tournament_category_state.py` | +120 lines |

---

## Tasks

### 1. [x] State — `_referee_count` variable + `_load_referee_count()` method

**File:** `kakumi_app/states/tournament_category_state.py`

**Changes:**

1. Add `func` to imports: change `from sqlmodel import select` → `from sqlmodel import func, select`
2. Add state variable after `form_scoring_type`: `_referee_count: int = 0`
3. Add private method `_load_referee_count(self) -> None` that executes
   `session.exec(select(func.count(Referee.id))).one()` inside `rx.session()`
   and assigns to `self._referee_count`

**Depends on:** Nothing
**Lines:** +7

---

### 2. [x] State — `judge_panel_warning` computed var

**File:** `kakumi_app/states/tournament_category_state.py`

**Changes:**
Add `@rx.var` method `judge_panel_warning(self) -> str` after
`has_selected_tournament_context`. Logic:

1. Normalize `self.modality` via `_normalize_modality()`
2. If modality is not `KATA_INDIVIDUAL` or `KATA_TEAM` → return `""`
3. Parse `int(self.form_judge_panel_size)`
4. If panel_size > `self._referee_count` → return `"Jueces disponibles: {count}. Panel requiere: {size}."`
5. Else → return `""`

**Depends on:** Task 1 (`_referee_count` must exist)
**Lines:** +12

---

### 3. [x] State — Wire `set_judge_panel_size()` to refresh referee count

**File:** `kakumi_app/states/tournament_category_state.py`

**Changes:**
Add `self._load_referee_count()` as the second line in
`set_judge_panel_size()`, after `self.form_judge_panel_size = value`.

**Depends on:** Task 1
**Lines:** +1

---

### 4. [x] State — Wire `set_form_values()` edit path to load referee count

**File:** `kakumi_app/states/tournament_category_state.py`

**Changes:**
Add `self._load_referee_count()` in the edit (`if category:`) block, right
before the early `return` (after all form values are set). This ensures
the warning is evaluated immediately when opening the edit form with a
pre-filled panel size.

Additionally call `self._load_referee_count()` in the create path
(the `else` branch) right after `self.reset_form()` so initial default
panel size of "3" is checked against real referee count.

**Depends on:** Task 1
**Lines:** +2

---

### 5. [x] UI — Add warning text in kata fields block

**File:** `kakumi_app/pages/tournament.py`

**Changes:**
Inside the kata fields `rx.vstack` (the block guarded by `(state.modality == "Kata Individual") | (state.modality == "Kata por Equipos")`),
add after the `judge_panel_size` select element:

```python
rx.cond(
    state.judge_panel_warning != "",
    rx.text(
        state.judge_panel_warning,
        color_scheme="amber",
        font_size="sm",
    ),
),
```

**Depends on:** Task 2 (`judge_panel_warning` var exists)
**Lines:** +8

---

### 6. [x] Tests — `_referee_count` initializes to zero

**File:** `tests/test_tournament_category_state.py`

**Scenario:** Fresh state → `_referee_count == 0`.

**Change:** Add `test_judge_panel_warning_initial_referee_count_is_zero`.
Instantiate state, assert `state._referee_count == 0`.

**Depends on:** Task 1
**Lines:** +8

---

### 7. [x] Tests — `_load_referee_count()` queries from DB

**File:** `tests/test_tournament_category_state.py`

**Scenario:** Insert 5 Referee records, call `_load_referee_count()`,
assert `_referee_count == 5`.

**Change:** Add `test_judge_panel_warning_load_referee_count_from_db`.
Create 5 Referee rows via `rx.session()`, call
`state._load_referee_count()`, assert count.

**Depends on:** Task 1
**Lines:** +14

---

### 8. [x] Tests — Warning visible on create when panel > referees

**File:** `tests/test_tournament_category_state.py`

**Scenario:** 2 Referees, create form, set panel to 7 → warning shown.

**Change:** Add `test_judge_panel_warning_on_create_when_panel_exceeds_referees`.
Create 2 Referees, set tournament context, open create form, set panel to 7,
assert `judge_panel_warning` contains expected text.

**Depends on:** Tasks 1–4 (state wired), Task 6/7 (test infra)
**Lines:** +18

---

### 9. [x] Tests — Warning visible on edit under same conditions

**File:** `tests/test_tournament_category_state.py`

**Scenario:** 2 Referees, edit existing kata category (panel=5) → warning shown.

**Change:** Add `test_judge_panel_warning_on_edit_when_panel_exceeds_referees`.
Use `sample_category` fixture (panel_size=5), create 2 Referees,
open edit form, assert warning text says "Panel requiere: 5."

**Depends on:** Tasks 1–4, Task 6/7
**Lines:** +16

---

### 10. [x] Tests — No warning when referees sufficient

**File:** `tests/test_tournament_category_state.py`

**Scenario:** 8 Referees, create form, panel=5 → no warning.

**Change:** Add `test_judge_panel_warning_no_warning_when_referees_sufficient`.
Create 8 Referees, open create form, set panel=5, assert
`judge_panel_warning == ""`.

**Depends on:** Task 8 pattern
**Lines:** +12

---

### 11. [x] Tests — Dropping panel size removes warning

**File:** `tests/test_tournament_category_state.py`

**Scenario:** 2 Referees, panel=7 → warning, then panel=3 → warning gone.

**Change:** Add `test_judge_panel_warning_dropping_panel_removes_warning`.
Set panel to 7 → assert warning, then set panel to 3 → assert warning empty.

**Depends on:** Task 8 pattern
**Lines:** +14

---

### 12. [x] Tests — No warning for kumite modality

**File:** `tests/test_tournament_category_state.py`

**Scenario:** 2 Referees, kumite modality → no warning regardless of panel size.

**Change:** Add `test_judge_panel_warning_no_warning_for_kumite`.
Set modality to kumite display value, set panel to 7, assert warning empty.

**Depends on:** Task 2 (var handles modality check)
**Lines:** +12

---

### 13. [x] Tests — Save succeeds with warning active

**File:** `tests/test_tournament_category_state.py`

**Scenario:** 2 Referees, panel=7, warning visible, save → success.

**Change:** Add `test_judge_panel_warning_save_succeeds_with_warning_active`.
Create 2 Referees, open create form, set panel=7, call `save_category`,
assert toast success and category persisted.

**Depends on:** Task 8 pattern, existing save test infra
**Lines:** +18

---

### 14. [x] Tests — Zero referees shows warning for any panel size

**File:** `tests/test_tournament_category_state.py`

**Scenario:** 0 Referees, panel=3 → warning for any non-zero panel.

**Change:** Add `test_judge_panel_warning_zero_referees_shows_warning`.
No Referee records, open create form, test all panel sizes (3, 5, 7)
all produce warning text.

**Depends on:** Task 8 pattern
**Lines:** +14

---

## Dependency Graph

```
Task 1 (state var + method)
  ├── Task 2 (warning var)
  │   └── Task 5 (UI)
  ├── Task 3 (wire set_judge_panel_size)
  ├── Task 4 (wire set_form_values)
  ├── Task 6 (test: init zero)
  └── Task 7 (test: load from DB)
       └── Task 8 (test: warning on create)
            ├── Task 9 (test: warning on edit)
            ├── Task 10 (test: sufficient referees)
            ├── Task 11 (test: drop panel)
            ├── Task 12 (test: kumite)
            ├── Task 13 (test: save succeeds)
            └── Task 14 (test: zero referees)
```

**Implementation order:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14
(1–5 implementation, 6–14 tests)

## Rollback

Single commit. `git revert <sha>` removes the feature cleanly. No migration
required — no schema changes.
