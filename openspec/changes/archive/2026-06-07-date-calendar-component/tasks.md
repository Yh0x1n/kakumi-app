# SDD Tasks — Date Calendar Popover for Tournament Dates

**Change**: `date-calendar-component`
**Phase**: Tasks (complete)
**Date**: 2026-06-07
**Author**: SDD tasks executor (subagent)

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~310–350 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | exception-ok |
| Chain strategy | pending |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

**Rationale**: Total delta is ~310 lines (120 new component + 85 new tests + 65 state + 30 registries + 10 test fix). Well within 400-line budget. Single PR is safe. No chained PRs needed. `pending` chain strategy because single-PR delivery doesn't require a chain.

---

## Phase 1: Infrastructure Setup

### 1.1 Create `kakumi_app/components/date_calendar.py` module skeleton

Create the file with module-level docstring, all imports (`calendar`, `datetime`, `reflex as rx`, `TournamentCrudState`), and empty function stubs:

- `_build_day_cells(year, month, selected_display) -> list[dict]` — return `[]`
- `_render_day_cell(cell) -> rx.Component` — return `rx.fragment()`
- `date_calendar_popover(*, value, on_change, target) -> rx.Component` — return `rx.box()`

**Stubs must compile** (no syntax errors, valid type hints).

**File path**: `kakumi_app/components/date_calendar.py`
**Verification**: `python -c "import ast; ast.parse(open('kakumi_app/components/date_calendar.py').read())"` produces no syntax errors.

---

## Phase 2: RED — Write Failing Tests

### 2.1 RED: Format helpers unit tests

Create `tests/test_date_calendar.py` with failing tests for the three format helpers (imported as module-level functions from `kakumi_app.states.tournament_crud_state`):

- **2.1.a** `test_iso_to_display_happy_path` — `_iso_to_display("2026-06-07")` → `"07/06/2026"`
- **2.1.b** `test_iso_to_display_empty` — `_iso_to_display("")` → `""`
- **2.1.c** `test_iso_to_display_invalid` — `_iso_to_display("not-a-date")` → `""`
- **2.1.d** `test_display_to_date_happy_path` — `_display_to_date("07/06/2026")` → `date(2026, 6, 7)`
- **2.1.e** `test_display_to_date_dash_variant` — `_display_to_date("07-06-2026")` → `date(2026, 6, 7)` (dash normalisation)
- **2.1.f** `test_display_to_date_invalid` — `_display_to_date("99/99/9999")` → `None`
- **2.1.g** `test_display_to_date_garbage` — `_display_to_date("abc")` → `None`
- **2.1.h** `test_display_to_date_empty` — `_display_to_date("")` → `None`
- **2.1.i** `test_date_to_iso` — `_date_to_iso(date(2026, 6, 7))` → `"2026-06-07"`

**Expected**: All 9 tests FAIL (ImportError or AttributeError because helpers don't exist yet).

### 2.2 RED: `_build_day_cells` grid structure tests

Add to `test_date_calendar.py`:

- **2.2.a** `test_build_day_cells_returns_list_of_dicts` — verifies shape (list of dicts with keys `day`, `is_current_month`, `is_selected`, `label`)
- **2.2.b** `test_build_day_cells_length_35_or_42` — verifies 5 or 6 weeks (35–42 items)
- **2.2.c** `test_build_day_cells_offset_first_week` — June 2026 starts on Monday → first cell (Sunday) has `day=0`, `is_current_month=False`
- **2.2.d** `test_build_day_cells_marks_selected_date` — selected_display="07/06/2026" produces exactly one cell with `is_selected=True` and `day=7`
- **2.2.e** `test_build_day_cells_no_selection` — selected_display="" produces all `is_selected=False`

**Expected**: All 5 tests FAIL (function returns `[]` stub).

### 2.3 RED: Calendar state vars and event handler tests

Add synchronous (non-async) tests that instantiate `TournamentCrudState` and inspect state vars, then call event handlers directly:

- **2.3.a** `test_calendar_state_vars_initial_values` — `show_calendar` is `False`, `calendar_target` is `""`, `calendar_month` is `0`, `calendar_year` is `0`
- **2.3.b** `test_toggle_calendar_opens_for_target` — call `toggle_calendar("start")` → `show_calendar` is `True`, `calendar_target` is `"start"`, `calendar_month`/`calendar_year` are current month/year (non-zero)
- **2.3.c** `test_toggle_calendar_closes_same_target` — call `toggle_calendar("start")` twice → `show_calendar` is `False`, `calendar_target` is `""`
- **2.3.d** `test_toggle_calendar_switches_target` — call `toggle_calendar("start")`, then `toggle_calendar("end")` → `show_calendar` is `True`, `calendar_target` is `"end"`
- **2.3.e** `test_calendar_prev_month_wraps_year` — set `calendar_month=1`, `calendar_year=2026`, call `calendar_prev_month()` → `calendar_month=12`, `calendar_year=2025`
- **2.3.f** `test_calendar_next_month_wraps_year` — set `calendar_month=12`, `calendar_year=2026`, call `calendar_next_month()` → `calendar_month=1`, `calendar_year=2027`
- **2.3.g** `test_calendar_select_day_sets_start_date` — set `calendar_target="start"`, `calendar_month=6`, `calendar_year=2026`, call `select_calendar_day(15)` → `start_date` is `"15/06/2026"`, `show_calendar` is `False`
- **2.3.h** `test_calendar_select_day_sets_end_date` — same but with `calendar_target="end"` → `end_date` is set
- **2.3.i** `test_calendar_select_day_closes_popover` — after `select_calendar_day`, verify `show_calendar=False`, `calendar_target=""`

**Expected**: All 9 tests FAIL (state vars not present / handlers not defined).

### 2.4 RED: Component contract tests

Add tests that verify the component function exists, is callable, and returns an `rx.Component`:

- **2.4.a** `test_date_calendar_popover_is_callable` — `callable(date_calendar_popover)` is `True`
- **2.4.b** `test_date_calendar_popover_returns_component` — call with dummy `value=rx.Var.create_safe("")`, `on_change=lambda x: None`, `target="start"` → result is `rx.Component`
- **2.4.c** `test_date_calendar_popover_includes_trigger` — rendered string contains `"DD/MM/AAAA"` placeholder text
- **2.4.d** `test_render_day_cell_returns_component_for_current_month` — `_render_day_cell({"day": 15, "is_current_month": True, "is_selected": False, "label": "15"})` returns `rx.Component`

**Expected**: Tests 2.4.a and 2.4.b MAY pass (stub returns `rx.box()` which is a Component). Tests 2.4.c and 2.4.d FAIL.

---

## Phase 3: GREEN — Make Tests Pass

### 3.1 GREEN: Implement format helpers

Add three module-level private functions at the top of `kakumi_app/states/tournament_crud_state.py` (after imports, before class definition):

```python
def _iso_to_display(iso_str: str) -> str:
    """Convert '2026-06-07' → '07/06/2026'. Return '' on failure."""
    ...

def _display_to_date(display_str: str) -> datetime.date | None:
    """Convert '07/06/2026' → date(2026,6,7). Return None on failure.
    Accepts 'DD-MM-YYYY' by normalising dashes to slashes."""
    ...

def _date_to_iso(d: datetime.date) -> str:
    """Convert date → '2026-06-07'."""
    ...
```

**Verification**: `python -m pytest tests/test_date_calendar.py::test_iso_to_display_happy_path tests/test_date_calendar.py::test_display_to_date_happy_path tests/test_date_calendar.py::test_date_to_iso -v` — all 3 PASS.

Then run all 9 format helper tests: `python -m pytest tests/test_date_calendar.py -k "test_iso_to_display or test_display_to_date or test_date_to_iso" -v` — all 9 PASS.

### 3.2 GREEN: Implement calendar state vars and event handlers

Add to `TournamentCrudState` class body (grouped under `# ── Calendar popover state ──` comment):

**State vars** (4 lines):
```python
show_calendar: bool = False
calendar_target: str = ""
calendar_month: int = 0
calendar_year: int = 0
```

**Event handlers** (4 methods):
- `toggle_calendar(self, target: str)` — toggle logic + init month/year from `datetime.date.today()` if uninitialized
- `calendar_prev_month(self)` — decrement month, wrap year at 1→12
- `calendar_next_month(self)` — increment month, wrap year at 12→1
- `select_calendar_day(self, day: int)` — build `datetime.date`, format as `"%d/%m/%Y"`, set `start_date` or `end_date` based on `calendar_target`, then close popover

**Key detail**: `select_calendar_day` must cast `day` to `int` (it comes from `rx.foreach` as a Python int, but ensure type safety).

**Verification**: `python -m pytest tests/test_date_calendar.py -k "test_calendar_state or test_toggle_calendar or test_calendar_prev or test_calendar_next or test_calendar_select" -v` — all 9 tests PASS.

### 3.3 GREEN: Implement `_build_day_cells` and `_render_day_cell`

In `kakumi_app/components/date_calendar.py`:

- **`_build_day_cells(year, month, selected_display)`**: Use `calendar.monthcalendar(year, month)` to build 35–42 dicts. Parse `selected_display` via `datetime.datetime.strptime(... , "%d/%m/%Y")` to determine `is_selected`. Each dict has `day`, `is_current_month`, `is_selected`, `label`.

- **`_render_day_cell(cell)`**: Return `rx.cond(cell["is_current_month"], rx.button(...), rx.box("", ...))` with day button. Apply highlight style when `cell["is_selected"]`. **Critical**: Use `functools.partial` or a factory function for the `on_click` lambda to avoid Python closure capture of the loop variable (per design R2 mitigation). Example:

    ```python
    def _make_on_click(day: int):
        return lambda: TournamentCrudState.select_calendar_day(day)

    # In _render_day_cell:
    on_click=_make_on_click(cell["day"]),
    ```

**Verification**: `python -m pytest tests/test_date_calendar.py -k "test_build_day_cells or test_render_day_cell" -v` — all 5 tests PASS.

### 3.4 GREEN: Implement `date_calendar_popover` component

Implement the full component function in `date_calendar.py`:

```python
def date_calendar_popover(
    *,
    value: rx.Var[str],
    on_change: rx.EventHandler,
    target: str,
) -> rx.Component:
```

Structure:
1. **Trigger**: `rx.select` (with `[value]` as single option) or `rx.button` styled as input — shows current DD/MM/YYYY value, calls `state.toggle_calendar(target)` on click
2. **Overlay**: `rx.cond` checking `state.show_calendar AND state.calendar_target == target`
3. **Overlay contents**:
   - Month navigation: `rx.hstack` with prev button, month name + year text, next button
   - Weekday header row: Spanish abbreviations `["Do", "Lu", "Ma", "Mi", "Ju", "Vi", "Sá"]`
   - Day grid: `rx.grid` with 7 cols, `rx.foreach` over `_build_day_cells(...)` and `_render_day_cell`
4. **Positioning**: `position="absolute"`, `z_index="100"`, white background, border, shadow

**Reactivity**: Since `_build_day_cells` is called with `state.calendar_year` and `state.calendar_month` (state vars), Reflex re-renders when these change. The list is passed to `rx.foreach` directly.

**Verification**: `python -m pytest tests/test_date_calendar.py -k "test_date_calendar_popover" -v` — all 4 tests PASS.

### 3.5 GREEN: Modify `set_form_values`, `save_tournament`, `_serialize_tournament`

In `kakumi_app/states/tournament_crud_state.py`:

**`set_form_values()`** — change ISO→DD/MM/YYYY conversion:
```python
# Replace:
self.start_date = tournament.get("start_date", "")
self.end_date = tournament.get("end_date") or self.start_date

# With:
self.start_date = _iso_to_display(tournament.get("start_date", ""))
self.end_date = _iso_to_display(
    tournament.get("end_date") or tournament.get("start_date", "")
)
```

**`save_tournament()`** — change date parsing:
```python
# Replace:
start_date = datetime.datetime.strptime(self.start_date, "%Y-%m-%d").date()
end_date = datetime.datetime.strptime(self.end_date, "%Y-%m-%d").date()
except ValueError:
    self.error_message = "Invalid date format (YYYY-MM-DD)"

# With:
start_date = _display_to_date(self.start_date)
end_date = _display_to_date(self.end_date)
if start_date is None or end_date is None:
    self.error_message = "Invalid date format (DD/MM/YYYY)"
    return
```

**`_serialize_tournament()`** — add display keys:
```python
# Add after start_date / end_date:
"start_date_display": _iso_to_display(tournament.start_date.isoformat()),
"end_date_display": _iso_to_display(tournament.end_date.isoformat()),
```

**Verification**: `python -m pytest tests/test_crud_registries_apply.py::test_tournament_crud_save_create_then_update -v` — this will FAIL because the test still uses ISO format dates. That's expected; task 3.7 fixes it.

### 3.6 GREEN: Update `registries.py`

Edit `kakumi_app/pages/registries.py`:

1. **Add import** at top:
   ```python
   from kakumi_app.components.date_calendar import date_calendar_popover
   ```

2. **Replace date form fields** in `_tournament_form()`:
   - Change heading label from `"Inicio (YYYY-MM-DD)"` to `"Inicio (DD/MM/AAAA)"`
   - Replace `rx.input` for start_date with:
     ```python
     date_calendar_popover(
         value=state.start_date,
         on_change=state.set_start_date,
         target="start",
     )
     ```
   - Same for end_date with `target="end"`

3. **Update table cell** in `_tournaments_card()`:
   - Change `tournament["start_date"]` to `tournament["start_date_display"]`

**Verification**: `python -c "from kakumi_app.components.date_calendar import date_calendar_popover; print('Import OK')"` — succeeds.  
`python -c "from kakumi_app.pages.registries import _tournament_form; print('Import OK')"` — succeeds.

### 3.7 GREEN: Update existing test assertions to DD/MM/YYYY format

Edit `tests/test_crud_registries_apply.py` — update 3 test functions (6 date-string assignments):

| Line(s) | Test | Old Value | New Value |
|---------|------|-----------|-----------|
| ~309–310 | `test_tournament_crud_save_create_then_update` | `"2027-03-01"`, `"2027-03-02"` | `"01/03/2027"`, `"02/03/2027"` |
| ~361–362 | `test_tournament_crud_save_update_preserves_existing_lifecycle_status` | `"2027-05-01"`, `"2027-05-02"` | `"01/05/2027"`, `"02/05/2027"` |
| ~1032–1033 | `test_tournament_crud_save_rolls_back_and_shows_toast_on_db_error` | `"2027-03-01"`, `"2027-03-02"` | `"01/03/2027"`, `"02/03/2027"` |

**Note**: No existing test checks the exact error message `"Invalid date format (YYYY-MM-DD)"`, so the error message change to `"Invalid date format (DD/MM/YYYY)"` does not break any assertions.

**Verification**: `python -m pytest tests/test_crud_registries_apply.py::test_tournament_crud_save_create_then_update tests/test_crud_registries_apply.py::test_tournament_crud_save_update_preserves_existing_lifecycle_status tests/test_crud_registries_apply.py::test_tournament_crud_save_rolls_back_and_shows_toast_on_db_error -v` — all 3 PASS.

### 3.8 GREEN: Run full test suite and confirm all GREEN

```bash
python -m pytest tests/test_date_calendar.py tests/test_crud_registries_apply.py -v --tb=short
```

**Expected**: All tests PASS.  
If any fail, fix immediately — do not proceed to next phase.

---

## Phase 4: TRIANGULATE — Strengthen Test Coverage

### 4.1 Add edge case tests for format helpers

Add to `test_date_calendar.py`:

- **4.1.a** `test_iso_to_display_none` — `_iso_to_display(None)` → `""` (type safety)
- **4.1.b** `test_display_to_date_edge_dates` — `"01/01/0001"` → `date(1, 1, 1)`, `"31/12/9999"` → `date(9999, 12, 31)`
- **4.1.c** `test_display_to_date_february_leap` — `"29/02/2024"` → `date(2024, 2, 29)` (leap year), `"29/02/2023"` → `None` (non-leap)
- **4.1.d** `test_iso_to_display_roundtrip` — `_display_to_date(_iso_to_display("2026-06-07"))` → `date(2026, 6, 7)`

**Verification**: `python -m pytest tests/test_date_calendar.py -k "test_iso_to_display or test_display_to_date" -v` — all edge cases PASS.

### 4.2 Add calendar navigation boundary tests

Add to `test_date_calendar.py`:

- **4.2.a** `test_calendar_prev_month_from_january` — set month=1, year=2026, call `calendar_prev_month()` → month=12, year=2025
- **4.2.b** `test_calendar_next_month_from_december` — set month=12, year=2026, call `calendar_next_month()` → month=1, year=2027
- **4.2.c** `test_toggle_calendar_reinitializes_month` — set `calendar_month=0`, call `toggle_calendar("start")` → month/year are non-zero (current date)
- **4.2.d** `test_toggle_calendar_preserves_month_if_already_set` — set `calendar_month=6`, `calendar_year=2026`, call `toggle_calendar("start")` → month stays 6, year stays 2026

**Verification**: `python -m pytest tests/test_date_calendar.py -k "test_calendar_prev or test_calendar_next or test_toggle_calendar" -v` — all PASS.

### 4.3 Add day cell rendering edge cases

- **4.3.a** `test_build_day_cells_february_non_leap` — February 2023 → 28 days, no cell has day=29
- **4.3.b** `test_build_day_cells_february_leap` — February 2024 → 29 days, cell with day=29 exists
- **4.3.c** `test_render_day_cell_empty_month` — `is_current_month=False` → renders `rx.box("", ...)` placeholder, not a button
- **4.3.d** `test_render_day_cell_uses_partial_for_closure` — Verify `_render_day_cell` avoids lambda closure issue by calling `_make_on_click(cell["day"])` or equivalent pattern. Code inspection test.

**Verification**: `python -m pytest tests/test_date_calendar.py -k "test_build_day_cells or test_render_day_cell" -v` — all PASS.

### 4.4 Verify all existing CRUD tests pass with new date format

```bash
python -m pytest tests/test_crud_registries_apply.py -v --tb=short
```

**Expected**: Every CRUD test GREEN. Pay special attention to tournament-related tests (save, update, delete, rollback).

---

## Phase 5: REFACTOR — Clean Up and Final Verification

### 5.1 Review and consolidate patterns

- Verify all function docstrings exist and use triple quotes
- Verify all type hints are correct (mypy-compatible syntax)
- Verify `# ── Calendar popover state ──` comment block clearly separates calendar state from CRUD state
- Verify no unused imports in any modified file
- Verify `_make_on_click` (or equivalent) closure mitigation is in place (critical per design R2)

**Verification**: Manual code review of all changed files.

### 5.2 Verify ≤ 400 changed lines

Run from project root:
```bash
git diff main --stat
```

Sum `additions + deletions` across all changed files. If > 400, identify areas to trim (e.g., combine test cases, reduce component inline styles).

**Expected**: Total ≤ 400. If exceeded, trim before proceeding.

### 5.3 Run final full test suite

```bash
python -m pytest tests/ -v --tb=short 2>&1
```

**Expected**: All tests GREEN (0 failed, 0 errors).

### 5.4 Verify ADR compliance

- **ADR-1**: Calendar state in `TournamentCrudState` (confirmed: no separate state created)
- **ADR-2**: Module-level helpers (confirmed: `_iso_to_display`, `_display_to_date`, `_date_to_iso` are module-level)
- **ADR-3**: `rx.cond` + positioned overlay (confirmed: no `rx.popover` usage)
- **ADR-4**: `rx.foreach` over computed list (confirmed: `_build_day_cells` returns plain list)
- **ADR-5**: Shared `calendar_target` (confirmed: single discriminator, not per-instance)

**Verification**: Read through each file change and confirm all ADRs are followed.

---

## Dependency Graph Between Tasks

```
1.1 (setup skeleton)
  ├── 2.1 (RED: format helpers) ──→ 3.1 (GREEN: format helpers)
  ├── 2.2 (RED: build_day_cells) ──→ 3.3 (GREEN: build_day_cells)
  ├── 2.3 (RED: state vars/handlers) ──→ 3.2 (GREEN: state vars)
  └── 2.4 (RED: component contract) ──→ 3.4 (GREEN: component)

3.1 ──→ 3.5 (GREEN: set_form_values, save, serialize)
3.2 ──→ 3.5 (needs state vars)
3.3 ──→ 3.4 (needs _build_day_cells for component)
3.5 ──→ 3.6 (GREEN: registries.py)
3.5 ──→ 3.7 (GREEN: update tests)
3.6, 3.7 ──→ 3.8 (GREEN: full suite)

3.8 ──→ 4.1, 4.2, 4.3, 4.4 (TRIANGULATE)
4.x ──→ 5.1, 5.2, 5.3, 5.4 (REFACTOR)
```

**Parallel opportunities**:
- Tasks 2.1, 2.2, 2.3, 2.4 (RED) can be written in the same file before any GREEN implementation
- Tasks 3.1 (format helpers) and 3.2 (state vars) are independent — can be done in any order
- Task 3.3 (build_day_cells) must precede 3.4 (component)
- Tasks 3.6 (registries.py) and 3.7 (test fixes) are independent but both depend on 3.5

---

## File-by-File Change Summary

| File | Action | Approx. Δ | Phase |
|------|--------|-----------|-------|
| `kakumi_app/components/date_calendar.py` | **Create** | +120 lines | 1.1, 3.3, 3.4 |
| `kakumi_app/states/tournament_crud_state.py` | **Modify**: +3 helpers, +4 state vars, +4 handlers, edit 3 methods | +65 lines | 3.1, 3.2, 3.5 |
| `kakumi_app/pages/registries.py` | **Modify**: +1 import, 2× field replacement, 1× table cell, 2× labels | +25 lines | 3.6 |
| `tests/test_date_calendar.py` | **Create**: ~20 test functions | +85 lines | 2.1–2.4, 4.1–4.3 |
| `tests/test_crud_registries_apply.py` | **Modify**: 6 date-string values | +3 / -3 (~6 lines touched) | 3.7 |
| **Total** | | **~301 lines** | |
| **Budget** | | **≤ 400 ✅** | |

## Risks to Watch

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Closure capture** in `rx.foreach` loop (R2) | Day clicks all select same date | Use `_make_on_click(day)` factory function (task 3.3) |
| **Reactivity**: `_build_day_cells` called as plain Python function, not `@rx.var` | Grid may not re-render on month change | If `rx.foreach` doesn't react, convert to `@rx.var` property on `TournamentCrudState` (design R1 mitigation) |
| **Existing test failure** from date format change | 3 tests fail after 3.5 | Fixed in task 3.7 — update assertions in same green phase |
| **`rx.select` UX** (dropdown arrow confusion) | Low severity | Monitor; switch to `rx.button` if UX review raises concern |
