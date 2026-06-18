# Design: Judge Panel Validation Warning on Category Form

**Feature:** Reactive advisory warning when selected panel size exceeds total Referee records in the DB.

**Status:** Approved for implementation
**Design author:** SDD Executor
**Target files:** `tournament_category_state.py`, `tournament.py`, `test_tournament_category_state.py`
**No-JavaScript constraint:** All changes are pure Python / Reflex Python — zero custom JS.

---

## 1. Data Flow Diagram

```
User                      Reflex Runtime                State (TournamentCategoryState)      DB
 │                             │                                   │                         │
 │ change panel_size ▼         │                                   │                         │
 │ ─────────────────────────> on_change=set_judge_panel_size       │                         │
 │                             │                                   │                         │
 │                             │   1. self.form_judge_panel_size = value                      │
 │                             │   2. self._load_referee_count() ──────  rx.session() ──────> │
 │                             │                                   │    SELECT COUNT(*)       │
 │                             │                                   │    FROM referees         │
 │                             │                                   │ <────── result ───────── │
 │                             │   3. self._referee_count = result                             │
 │                             │                                   │                         │
 │                             │   4. judge_panel_warning @rx.var                             │
 │                             │      → reads modality, form_judge_panel_size, _referee_count │
 │                             │      → returns "Jueces disponibles: X. Panel requiere: Y."   │
 │                             │         OR "" if condition not met                            │
 │                             │                                   │                         │
 │  warning text re-renders ◄──┘   rx.cond(state.judge_panel_warning != "", ...)              │
 │                                                                                            │
 │  [form submission path — unmodified]                                                       │
 │  Guardar → save_category() → _validate_form() → ignores _referee_count entirely            │
 │                             │   → commits to DB regardless of warning state                │
```

### Create path flow (on form open)

```
set_form_values(_, category=None)
  │
  ├── self.reset_form()              → form_judge_panel_size = "3" (default)
  ├── self._set_form_open(False)
  ├── self._load_referee_count()     → queries COUNT(*), sets _referee_count
  │
  ▼
  judge_panel_warning @rx.var        → renders warning for default "3" if needed
```

### Edit path flow (on form open)

```
set_form_values(_, category={...})
  │
  ├── self.form_judge_panel_size = str(category["judge_panel_size"])  (e.g. "5")
  ├── ... other fields ...
  ├── self._load_referee_count()     → queries COUNT(*), sets _referee_count
  ├── return
  │
  ▼
  judge_panel_warning @rx.var        → renders warning for panel=5 if needed
```

---

## 2. Component / Class Changes

### 2.1 `TournamentCategoryState` — new variable

```python
# After `form_scoring_type: str = "average-with-discard"`
_referee_count: int = 0
```

**Rationale:** Private underscore prefix (`_`) keeps it out of serialized state sent to the browser — the frontend doesn't need this value directly; it only reads the computed `judge_panel_warning` string. Default `0` means the warning flashes only if panel size is non-zero on a truly empty DB, which is correct.

### 2.2 `TournamentCategoryState` — new private method

```python
def _load_referee_count(self) -> None:
    """Query total Referee count from DB and store in _referee_count."""
    with rx.session() as session:
        self._referee_count = session.exec(
            select(func.count(Referee.id))
        ).one()
```

**Key code decisions:**

| Decision | Choice | Why |
|----------|--------|-----|
| `func.count(Referee.id)` vs fetching all rows | `func.count()` | Single SQL `SELECT COUNT(*)` returns one integer. Fetching all `Referee` rows and `len()` in Python would transfer N rows over the wire. `count()` is O(1) index scan, imperceptible even for large referee tables. |
| `referee.id` vs `*` | Primary key column | PK index is smallest possible, fastest count. Same result as `COUNT(*)` since `id` is NOT NULL. |
| No `is_available` or role filter | See product decision | Per explicit user Q&A: count ALL referees regardless of role or availability. The match loader has its own availability logic later. |
| `rx.session()` context manager | Existing pattern | Every other DB-accessing method in this state uses `with rx.session()`. Consistent. |

### 2.3 `TournamentCategoryState` — new `@rx.var`

```python
@rx.var
def judge_panel_warning(self) -> str:
    """Advisory warning string when panel size > available referees.
    Returns localized Spanish warning or empty string."""
    normalized = self._normalize_modality(self.modality)
    if normalized not in {Modality.KATA_INDIVIDUAL.value, Modality.KATA_TEAM.value}:
        return ""
    try:
        panel_size = int(self.form_judge_panel_size)
    except (ValueError, TypeError):
        return ""
    if panel_size > self._referee_count:
        return f"Jueces disponibles: {self._referee_count}. Panel requiere: {panel_size}."
    return ""
```

**Why `@rx.var` instead of inline in the template?**

| Approach | Assessment |
|----------|------------|
| `@rx.var` (computed property) | ✅ Reactive — Reflex auto-recomputes when `modality`, `form_judge_panel_size`, or `_referee_count` change. Template stays clean: one `rx.cond` line. |
| Inline logic in `tournament.py` | ❌ Mixes business logic into the presentation layer. Would need to duplicate the comparison in every template. Not testable in isolation. |
| Regular method called manually | ❌ Would require manual invalidation and re-triggering from every mutation point. `@rx.var` gives this for free. |

**Reactivity dependencies tracked by Reflex:**

- `self.modality` — changes when the modality dropdown changes
- `self.form_judge_panel_size` — changes when `set_judge_panel_size()` fires
- `self._referee_count` — changes when `_load_referee_count()` completes

When any of these change between state mutations, Reflex recomputes the var before the next render cycle.

**Edge case handling in the var:**

- Non-kata modality → `""` (no DOM element rendered downstream)
- Malformed/empty `form_judge_panel_size` → `""` (defensive parse)
- Panel ≤ referee count → `""` (condition not met)
- Panel > referee count → localized warning string

### 2.4 `set_judge_panel_size()` — wire refresh

```python
def set_judge_panel_size(self, value: str) -> None:
    """Set judge panel size field and refresh referee count."""
    self.form_judge_panel_size = value
    self._load_referee_count()  # ← NEW LINE
```

**Why here:** Every dropdown `on_change` fires this handler. Adding the DB refresh here guarantees the warning is always current. The `on_change` fires both on user interaction AND on programmatic value changes from `set_form_values()` — wait, actually `set_form_values()` directly sets `self.form_judge_panel_size = str(...)`, it doesn't call `set_judge_panel_size()`. That's why we also need wiring in `set_form_values()` (see next section).

**Performance note:** Each dropdown change triggers a `COUNT(*)`. This is a single integer read from the PK index. With thousands of referees, this is under 1ms. No caching needed.

### 2.5 `set_form_values()` — wire for both edit and create paths

**Edit path** (the `if category:` block) — add before the `return`:

```python
# After all form fields are set (including form_judge_panel_size)
self._load_referee_count()
```

**Create path** (the `else` block) — add after `self.reset_form()`:

```python
self.reset_form()
self._load_referee_count()  # ← NEW LINE
self._set_form_open(editing=False)  # existing
```

Wait — order matters. `_load_referee_count()` should run after `form_judge_panel_size` has its final value. In the edit path, all fields including `form_judge_panel_size` are set before the return. In the create path, `reset_form()` sets `form_judge_panel_size = "3"`. So calling `_load_referee_count()` right after `reset_form()` is correct; `_set_form_open` doesn't change any panel-related fields.

**Actual placement (see tasks 4):**

```python
# Edit path — just before the early `return`
...
self.form_scoring_type = category.get("scoring_type", "average-with-discard")
self._load_referee_count()   # ← NEW
return

# Create path — right after reset_form
self.reset_form()
self._load_referee_count()   # ← NEW
self._set_form_open(editing=False)
```

### 2.6 Import change

```python
# Before:
from sqlmodel import select
# After:
from sqlmodel import func, select
```

Plus add import for the `Referee` model (already imported? Let's check.)

Looking at existing imports: `Referee` is NOT currently imported in `tournament_category_state.py`. We need to add:

```python
from kakumi_app.models.referee_model import Referee
```

### 2.7 UI — `_categories_card()` in `tournament.py`

Insert after the `judge_panel_size` `rx.select` inside the kata-fields `rx.vstack`:

```python
rx.select(
    ["3", "5", "7"],
    value=state.form_judge_panel_size,
    on_change=state.set_judge_panel_size,
),
# ── NEW: advisory warning ──────────────────────────────────
rx.cond(
    state.judge_panel_warning != "",
    rx.text(
        state.judge_panel_warning,
        color_scheme="amber",
        font_size="sm",
    ),
),
# ── end new ────────────────────────────────────────────────
```

**Why `rx.cond` + `rx.text` instead of always rendering an empty element?**

| Approach | Verdict |
|----------|---------|
| `rx.cond(condition, rx.text(...))` | ✅ No DOM element when warning is inactive. Clean. |
| Always render `rx.text(...)` with empty string | ❌ Would add an invisible DOM node. Still takes layout space if `min_height` or padding is set. More bytes sent to client. |

**Why `color_scheme="amber"`?** Matches Reflex's built-in warning color token. Amber is visually distinct from error (red) and success (green). Readable on light and dark backgrounds.

**Why `font_size="sm"`?** Inline advisory text should be smaller than the form field labels. `sm` is the standard Reflex small size.

### 2.8 No changes to `_validate_form()`, `save_category()`, or any persistence logic

The warning is purely advisory. The `_referee_count` variable and `judge_panel_warning` var are never read by `_validate_form()`. The `save_category()` flow is identical to today. This is intentional — per spec requirements, the warning must NOT block saving.

---

## 3. Sequence of Operations

### 3.1 Create path — user opens form

```
1. User clicks "Nueva categoría"
2. State: set_form_values(_, category=None)
      → reset_form()                # form_judge_panel_size = "3"
      → _load_referee_count()       # DB query → _referee_count = N
      → _set_form_open(editing=False)
3. Reflex re-render:
      → judge_panel_warning @rx.var recomputes
      → If N < 3 → warning shown with "Panel requiere: 3."
      → If N ≥ 3 → no warning
4. User changes panel_size to "7"
5. State: set_judge_panel_size("7")
      → form_judge_panel_size = "7"
      → _load_referee_count()       # DB query → _referee_count = N
6. Reflex re-render:
      → judge_panel_warning recomputes
      → If N < 7 → warning shown
      → If N ≥ 7 → no warning
```

### 3.2 Edit path — user opens existing category

```
1. User clicks "Editar" on a kata category (sample_category with judge_panel_size=5)
2. State: set_form_values(_, category={...})
      → current_category = category dict
      → form_judge_panel_size = str(category["judge_panel_size"])  # "5"
      → ... all other fields set ...
      → _load_referee_count()       # DB query → _referee_count = N
      → return (no _set_form_open called — it's already called earlier)
3. Reflex re-render:
      → judge_panel_warning recomputes
      → If N < 5 → warning "Jueces disponibles: N. Panel requiere: 5."
      → If N ≥ 5 → no warning
```

### 3.3 Save with warning active

```
1. Warning is visible (panel_size > referee count)
2. User clicks "Guardar categoría"
3. State: save_category()
      → _validate_form()
           → validates form fields (name, ages, belts, modality, etc.)
           → validates kata fields (panel size ∈ {3,5,7}, flow mode, scoring type)
           → does NOT check _referee_count at all
           → returns payload dict (or None if validation fails)
      → payload is not None
      → DB INSERT/UPDATE in rx.session()
      → show_form = False, reset_form()
      → rx.toast.success(message)
4. Category is saved regardless of warning state
```

### 3.4 Modality switch to kumite

```
1. User changes modality from "Kata Individual" to "Kumite Individual"
2. State: set_modality("Kumite Individual")
      → modality = "Kumite Individual"
3. Reflex re-render:
      → kata-fields rx.cond becomes false → entire kata block hidden
      → judge_panel_warning @rx.var recomputes
      → normalized modality is KUMITE_INDIVIDUAL → returns ""
      → rx.cond in UI → no DOM element rendered
```

---

## 4. Test Plan

All tests go in `tests/test_tournament_category_state.py`. New tests are `@pytest.mark.anyio` async tests matching the existing test style.

### 4.1 `test_judge_panel_warning_initial_referee_count_is_zero`

- Instantiate `TournamentCategoryState` (no DB setup)
- Assert `state._referee_count == 0`

### 4.2 `test_judge_panel_warning_load_referee_count_from_db`

- Create 5 `Referee` rows via `rx.session()`
- Call `state._load_referee_count()`
- Assert `state._referee_count == 5`

### 4.3 `test_judge_panel_warning_on_create_when_panel_exceeds_referees`

- Create 2 Referees
- Set tournament context via `set_tournament_context`
- Call `set_form_values(_, None)` (create path)
- Set panel to "7" via `set_judge_panel_size("7")`
- Assert `state.judge_panel_warning == "Jueces disponibles: 2. Panel requiere: 7."`

### 4.4 `test_judge_panel_warning_on_edit_when_panel_exceeds_referees`

- Create 2 Referees
- Use `sample_category` fixture (has `judge_panel_size=5`)
- Set tournament context
- Call `set_form_values(_, category_serialized)` (edit path)
- Assert warning contains "Panel requiere: 5."

### 4.5 `test_judge_panel_warning_no_warning_when_referees_sufficient`

- Create 8 Referees
- Create path → panel="5"
- Assert `state.judge_panel_warning == ""`

### 4.6 `test_judge_panel_warning_dropping_panel_removes_warning`

- Create 2 Referees
- Set panel="7" → assert warning visible
- Set panel="3" → assert `judge_panel_warning == ""`

### 4.7 `test_judge_panel_warning_no_warning_for_kumite`

- Create 2 Referees
- Create path → set modality to "Kumite Individual"
- Set panel="7"
- Assert `judge_panel_warning == ""`

### 4.8 `test_judge_panel_warning_save_succeeds_with_warning_active`

- Create 2 Referees
- Create path → panel="7" → warning visible
- Call `save_category()` with valid form data
- Assert toast success (monkeypatch `rx.toast.success`)
- Assert category persisted in DB

### 4.9 `test_judge_panel_warning_zero_referees_shows_warning`

- No Referee records (DB has 0)
- Create path → test panel="3", "5", "7" all produce warning
- Warning text says "Jueces disponibles: 0."

---

## 5. File Change Summary

| File | Lines changed | Nature |
|------|---------------|--------|
| `kakumi_app/states/tournament_category_state.py` | ~+25 | Imports (+2), state var (+1), method (+6), @rx.var (+12), wire set_judge_panel_size (+1), wire set_form_values (+2) |
| `kakumi_app/pages/tournament.py` | ~+8 | `rx.cond` + `rx.text` after panel size select |
| `tests/test_tournament_category_state.py` | ~+120 | 9 new test scenarios |

**Total:** ~153 lines (within 400-line review budget). Single commit, no schema changes, no migrations.

---

## 6. Rollback & Risk

**Rollback:** `git revert <sha>` — no schema changes, no migration, no cascading side effects.

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| DB `COUNT(*)` on every dropdown change | Low | Lightweight PK index scan. Even with 10K referees, imperceptible. |
| Warning briefly shows "0" before first DB query resolves | Low | Default `_referee_count=0` — warning appears for 1 render frame, then resolves when `set_form_values` fires `_load_referee_count()`. Not a real problem — the form takes multiple frames to render anyway. |
| Existing tests break | Low | No existing test calls `set_judge_panel_size` or touches `_referee_count`. The `set_judge_panel_size` method previously had 1 line, now has 2 — not a breaking change. |
| `_referee_count` causes state serialization overhead | None | Private `_` vars are excluded from Reflex serialization. |

---

## 7. Compliance with Constraints

| Constraint | How it's met |
|------------|--------------|
| No JavaScript | All changes are Python: `rx.cond`, `rx.text`, `@rx.var`, `func.count()`. |
| Pure Reflex components | UI uses `rx.cond` + `rx.text` — no custom HTML/CSS. |
| WKF 2026 compliance | Advisory only — doesn't alter any scoring or judging logic. |
| No new dependencies | `func` from `sqlmodel` (already transitive). `Referee` model import (already exists in codebase). |
| Test coverage | 9 new test scenarios covering all acceptance criteria. |
