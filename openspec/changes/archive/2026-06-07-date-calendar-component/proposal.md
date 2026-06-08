# SDD Proposal — Date Calendar Popover for Tournament Dates

**Change**: `date-calendar-component`  
**Status**: Draft for user review  
**Date**: 2026-06-07  
**Author**: SDD proposal executor (subagent)

---

## 1. Intent

Replace the two plain `rx.input` text fields for tournament dates (`start_date`, `end_date`) with an `rx.select` trigger that opens a mini month-grid calendar popover. The goal is to improve UX by eliminating manual ISO‑date entry and preventing format errors, while keeping the **DD/MM/YYYY** display convention throughout the UI.

---

## 2. Scope

### 2.1 In Scope

| Area | Detail |
|------|--------|
| `registries.py` — tournament form | Replace 2× `rx.input` with `rx.select` + calendar popover; update heading labels to `"Inicio (DD/MM/AAAA)"` / `"Fin (DD/MM/AAAA)"` |
| `registries.py` — tournament table | Show formatted `start_date_display` / `end_date_display` keys instead of raw ISO |
| `tournament_crud_state.py` — helpers | Add `_iso_to_display(iso_str) → str`, `_display_to_date(display_str) → date\|None`, `_date_to_iso(d) → str` |
| `tournament_crud_state.py` — `set_form_values()` | Convert ISO → DD/MM/YYYY when populating form fields |
| `tournament_crud_state.py` — `save_tournament()` | Parse DD/MM/YYYY instead of `%Y-%m-%d`; accept DD-MM-YYYY fallback via `.replace("-","/")` |
| `tournament_crud_state.py` — `_serialize_tournament()` | Add `start_date_display` / `end_date_display` keys |
| `components/date_calendar.py` | **New file**: Pure Reflex calendar popover component (month grid, prev/next nav, day selection) |
| Tests | New TDD test file for format helpers + component; update existing `test_crud_registries_apply.py` assertions |

### 2.2 Out of Scope (non‑goals, MUST NOT change)

- `Tournament` DB model — stays `datetime.date`; no migration
- Services (`results_service.py`, `export_service.py`) — keep ISO format
- Viewer (`viewer_state.py`, `viewer_service.py`) — keep ISO via `model_dump(mode="json")`
- Athlete / Referee date fields — not affected
- i18n / locale switching — not implemented
- Date range validation (`end_date < start_date`) — deferred to follow-up
- Mobile touch target optimisation — basic responsive sizing only

---

## 3. Requirements (RFC 2119)

### 3.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| REQ-FMT-01 | A helper function `_iso_to_display(iso_str: str) -> str` **SHALL** convert an ISO date string `"2026-06-07"` to `"07/06/2026"`. | MUST |
| REQ-FMT-02 | A helper function `_display_to_date(display_str: str) -> datetime.date \| None` **SHALL** parse `"DD/MM/YYYY"` and return a `date` object. | MUST |
| REQ-FMT-03 | `_display_to_date` **SHOULD** also accept `"DD-MM-YYYY"` by normalising dashes to slashes before parsing. | SHOULD |
| REQ-FMT-04 | `_display_to_date` **SHALL** return `None` for any string that cannot be parsed as a valid date after normalisation. | MUST |
| REQ-FMT-05 | A helper `_date_to_iso(d: datetime.date) -> str` **SHALL** return `d.isoformat()`. | MUST |
| REQ-FMT-06 | `set_form_values()` **SHALL** call `_iso_to_display()` on `tournament["start_date"]` and `tournament["end_date"]` before assigning to state vars. | MUST |
| REQ-FMT-07 | `save_tournament()` **SHALL** call `_display_to_date()` on `self.start_date` and `self.end_date` instead of `strptime(..., "%Y-%m-%d")`. | MUST |
| REQ-FMT-08 | `_serialize_tournament()` **SHALL** include keys `start_date_display` and `end_date_display` with DD/MM/YYYY values alongside the existing ISO `start_date`/`end_date` keys. | MUST |
| REQ-UI-01 | The tournament form **SHALL** replace each `rx.input` date field with an `rx.select` that shows the current DD/MM/YYYY value and triggers a calendar popover on focus/click. | MUST |
| REQ-UI-02 | The calendar popover **SHALL** render a month grid with day cells, prev/next month navigation, and a click handler that sets the selected date. | MUST |
| REQ-UI-03 | The calendar popover **SHALL** use `rx.cond` to toggle visibility (positioned `rx.box` overlay). If Reflex 0.8.28.post1 provides `rx.popover`, that **MAY** be used instead. | SHOULD |
| REQ-UI-04 | The tournament table **SHALL** display `start_date_display` instead of the raw ISO `start_date` column. | MUST |
| REQ-UI-05 | Heading labels **SHALL** change from `"Inicio (YYYY-MM-DD)"` to `"Inicio (DD/MM/AAAA)"` (and same for `"Fin"`). | MUST |
| REQ-DEF-01 | Import‑defensive normalisation: any user‑typed value with dashes **SHALL** have `"-"` replaced with `"/"` before parsing. | MUST |

### 3.2 Non‑Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| REQ-NFR-01 | Change **SHALL** not exceed 400 changed lines total (new + modified). | MUST |
| REQ-NFR-02 | Zero new external dependencies. | MUST |
| REQ-NFR-03 | All existing tests **SHALL** pass after updates (green suite). | MUST |
| REQ-NFR-04 | New format helpers **SHALL** be covered by TDD RED tests before implementation. | MUST |
| REQ-NFR-05 | Backward compatibility: `_serialize_tournament()` **MUST** keep existing `start_date`/`end_date` ISO keys so service layers continue to work unchanged. | MUST |

---

## 4. Affected Areas

### 4.1 Files to Modify

| File | Change Summary | Approx. Δ |
|------|---------------|-----------|
| `kakumi_app/states/tournament_crud_state.py` | Add 3 helpers; modify `set_form_values()`, `save_tournament()`, `_serialize_tournament()` | ~40 lines |
| `kakumi_app/pages/registries.py` | Replace 2× `rx.input` + labels in form; update table cell binding to `start_date_display` | ~30 lines |

### 4.2 Files to Create

| File | Purpose | Approx. size |
|------|---------|-------------|
| `kakumi_app/components/date_calendar.py` | Reusable calendar popover component (`date_calendar_popover()`) | ~100 lines |

### 4.3 Test Files

| File | Action | Approx. Δ |
|------|--------|-----------|
| `tests/test_crud_registries_apply.py` | Update ~6 date-string assertions (ISO → DD/MM/YYYY) | ~10 lines |
| `tests/test_date_calendar.py` | **New**: TDD RED tests for format helpers + component render | ~80 lines |

### 4.4 Unchanged (Verified)

| File | Reason |
|------|--------|
| `kakumi_app/models/tournament_model.py` | Model stays `datetime.date` |
| `kakumi_app/states/base_crud_state.py` | No date logic |
| `kakumi_app/services/results_service.py` | Uses `str(date)` — ISO for API |
| `kakumi_app/services/export_service.py` | Uses `.isoformat()` — ISO for export |
| `kakumi_app/states/viewer_state.py` | Uses `model_dump(mode="json")` — ISO |
| `kakumi_app/services/viewer_service.py` | Same as viewer_state |
| `tests/conftest.py` | Creates `Tournament(datetime.date(...))` directly |
| Alembic migrations | No schema change |

### 4.5 Package/Dependency Impact

**None.** The change uses only built-in Reflex 0.8.28.post1 components (`rx.select`, `rx.grid`, `rx.button`, `rx.cond`, `rx.box`, `rx.text`, `rx.hstack`, `rx.vstack`). The `@radix-ui/react-popover` package already exists in the `.web/bun.lock` as a transitive dependency of `radix-ui`, so no new JS packages are needed.

---

## 5. Architecture & Design Sketch

### 5.1 Data Flow

```
User selects date in popover
        │
        ▼
date_calendar.py: on_select("DD/MM/YYYY")
        │
        ▼
tournament_crud_state.py: set_start_date("DD/MM/YYYY")
        │
        ▼
Save flow:  _display_to_date("DD/MM/YYYY") → datetime.date → DB
        │
        ▼
Load flow:  DB → datetime.date → _serialize_tournament()
              ├── start_date: "2026-06-07"      (ISO, existing)
              └── start_date_display: "07/06/2026"  (DD/MM/YYYY, new)
```

### 5.2 Component Tree

```
_tournament_form()
  └── row
        ├── rx.vstack
        │     ├── rx.heading("Inicio (DD/MM/AAAA)")
        │     └── date_calendar_popover(
        │             value=state.start_date,
        │             on_change=state.set_start_date,
        │         )
        └── rx.vstack
              ├── rx.heading("Fin (DD/MM/AAAA)")
              └── date_calendar_popover(
                      value=state.end_date,
                      on_change=state.set_end_date,
                  )
```

### 5.3 Calendar Popover Mechanism

Since `rx.popover` is not used anywhere in the codebase and `rx.dialog` (used for sidebar/kumite) is modal-heavy, the recommended approach is:

1. **Trigger**: `rx.select` or `rx.button` showing the current DD/MM/YYYY value
2. **Overlay**: A positioned `rx.box` with `rx.cond(show_calendar, ...)` for visibility
3. **Grid**: A simple `rx.grid` with 7 columns (Sun–Sat), `rx.foreach` over day numbers
4. **Nav**: Prev/next month `rx.button` changing a `calendar_month` state var

Alternatively, if Reflex 0.8.28.post1 exposes `rx.popover`, prefer that for correct focus‑trapping and dismiss‑on‑click‑outside behaviour.

### 5.4 Serialisation Contract

```python
def _serialize_tournament(self, tournament: Tournament) -> dict[str, Any]:
    return {
        "id": tournament.id,
        "name": tournament.name,
        "venue": tournament.venue,
        "status": tournament.status,
        "start_date": tournament.start_date.isoformat(),         # unchanged
        "end_date": tournament.end_date.isoformat(),             # unchanged
        "start_date_display": self._iso_to_display(              # NEW
            tournament.start_date.isoformat()
        ),
        "end_date_display": self._iso_to_display(                # NEW
            tournament.end_date.isoformat()
        ),
        "tatami_count": tournament.tatami_count,
        "created_by_id": tournament.created_by_id,
    }
```

---

## 6. Risks & Mitigations

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R1 | `_iso_to_display()` fails on unexpected ISO format | Medium | Medium | Robust `strptime` + try/except; return empty string on failure |
| R2 | Existing test assertions with `"2027-03-01"` format fail | **Certain** | High | Bulk update all affected assertions; run full test suite before PR |
| R3 | `_display_to_date()` receives empty string when form is reset | Medium | Low | Return `None` on empty input — `save_tournament` already guards with `_validate_form()` |
| R4 | `dd-mm-yyyy` variant entered via keyboard | Low | Low | `.replace("-", "/")` before parse |
| R5 | Calendar component has no precedent — may need iteration | Medium | Low | Start with minimal grid; defer polish to spec phase |
| R6 | `rx.popover` unavailable → must build custom overlay | Medium | Low | Fallback to `rx.cond` + positioned `rx.box` — proven pattern in codebase |
| R7 | `set_form_values` called with `None` tournament (create mode) | Low | Medium | Already guarded in current code; ensure helper guards |
| R8 | Regression: service layers accidentally receive DD/MM/YYYY | Low | High | `_serialize_tournament` keeps ISO keys; only table uses display keys |

---

## 7. Rollback Plan

### 7.1 During Development (single PR)

```bash
git checkout main
# Branch is discarded; no impact
```

### 7.2 After Merge (if hotfix needed)

1. Identify the commit: `git log --oneline --grep="date-calendar-component"`
2. Revert: `git revert <commit-hash>`
3. Verify: `uv run python -m pytest tests/test_crud_registries_apply.py -v`

### 7.3 Data Safety

No migration → no data transformation risk. The DB always stores `datetime.date`. If the UI change has a bug, dates in the DB remain correct and recoverable by typing ISO format back into the old input (during rollback period).

---

## 8. Success Criteria

| Criterion | How to verify |
|-----------|---------------|
| All format helpers pass unit tests | `uv run python -m pytest tests/test_date_calendar.py -v` — all GREEN |
| All existing CRUD tests pass | `uv run python -m pytest tests/test_crud_registries_apply.py -v` — all GREEN |
| Full test suite passes | `uv run python -m pytest tests/ -v --tb=short` — no regressions |
| Form shows DD/MM/YYYY on edit | Open edit form for existing tournament → fields show `"01/06/2026"` |
| Table displays DD/MM/YYYY | Tournament row shows `"01/06/2026"` in "Inicio" column |
| New tournament saves correctly | Fill form, submit → date stored as `datetime.date` in DB |
| Dash variant accepted | Type `"01-06-2026"` → parsed as 1 June 2026 |
| Garbage rejected | Type `"not-a-date"` → error message shown |
| Changed lines ≤ 400 | `git diff main --stat` |

---

## 9. Proposal Question Round

Before finalising this proposal, the following questions would benefit from user input:

1. **Popover mechanism**: The codebase lacks `rx.popover` usage. Should we (a) build a lightweight positioned `rx.box` overlay toggled by `rx.cond`, or (b) attempt `rx.popover` (which may exist in Reflex 0.8.28 but is unused), or (c) use `rx.dialog` as a proven fallback?

2. **Table display format**: The exploration suggests adding `start_date_display` / `end_date_display` keys so the table shows DD/MM/YYYY. However, the table currently reads `tournament["start_date"]` directly. Is showing DD/MM/YYYY in the table a requirement, or should the table stay ISO?

3. **Create‑mode default date**: When creating a new tournament, should the date fields start empty (current behaviour) or pre‑fill with today's date in DD/MM/YYYY?

4. **Edge case — single‑day tournament**: If `start_date == end_date`, should the UI show both fields or auto‑fill the end date when start changes?

5. **Scope boundary**: The `end_date < start_date` validation is explicitly deferred. Is that acceptable, or should we include basic range validation in this PR?

---

## 10. Change Budget (Lines)

| Category | Estimated Δ |
|----------|-------------|
| New `date_calendar.py` | +100 |
| New `test_date_calendar.py` | +80 |
| `tournament_crud_state.py` modifications | +40 |
| `registries.py` modifications | +30 |
| `test_crud_registries_apply.py` modifications | +10 |
| **Total estimate** | **~260** |
| **Budget** | **≤ 400** ✅ |

This leaves ~140 lines of headroom for review feedback and polish.

---

## 11. Summary of Assumptions (Pending Confirmation)

- `rx.popover` is either unavailable or not preferred → custom `rx.cond` overlay
- Table **should** show DD/MM/YYYY (via new display keys)
- Create mode keeps empty date fields
- Single‑day tournaments: both fields shown independently; no auto‑fill
- Date range validation deferred

If these assumptions are incorrect, the proposal should be adjusted before proceeding to spec.
