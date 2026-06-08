Here is the complete exploration deliverable:

---

# SDD Explore — Date Calendar Popover for Tournament Dates

**Phase**: `explore`  
**Change**: Replace plain `rx.input` date fields with `rx.select` + calendar popover in tournament form  
**Format**: DD/MM/YYYY  
**Date**: 2026-06-07  
**Strict TDD**: ✅ activated

---

## 1. Scope

### ✅ In Scope
- Tournament form date fields (`start_date`, `end_date`) → `rx.select` + calendar popover
- Date parse logic: now DD/MM/YYYY (with DD-MM-YYYY fallback via `.replace("-","/")`)
- Form field display: `set_form_values` converts ISO→DD/MM/YYYY
- New reusable component: `kakumi_app/components/date_calendar.py`
- All related tests updated

### ❌ Out of Scope
- `Tournament` model stays `datetime.date` — no DB changes, no migration
- Export/service layers keep ISO format (`.isoformat()`, `str(date)`)
- Date range validation (`end_date < start_date`)
- Athlete/Referee date fields (nonexistent)
- i18n / locale switching

---

## 2. Current Implementation Trace (Confirmed)

| Layer | File | Current behaviour |
|-------|------|------------------|
| **Model** | `tournament_model.py` | `start_date: datetime.date`, `end_date: datetime.date` |
| **State vars** | `tournament_crud_state.py` | `start_date: str = ""`, `end_date: str = ""` |
| **State parse** | `tournament_crud_state.py` (save_tournament) | `strptime(self.start_date, "%Y-%m-%d")` |
| **State serialize** | `tournament_crud_state.py` (_serialize_tournament) | `.isoformat()` → "2026-06-07" |
| **State set_form** | `tournament_crud_state.py` (set_form_values) | `tournament.get("start_date", "")` → receives ISO |
| **UI form** | `registries.py` lines 433-450 | Two `rx.input` with placeholder "Inicio (YYYY-MM-DD)" |
| **UI table** | `registries.py` line 663 | `tournament["start_date"]` shows raw ISO |
| **Services** | `results_service.py`, `export_service.py` | `str(date)` / `.isoformat()` → ISO |
| **Viewer** | `viewer_state.py` | `model_dump(mode="json")` → ISO |

---

## 3. Affected Files (Complete)

### Must change

| File | Lines | Nature of change |
|------|-------|-----------------|
| `kakumi_app/pages/registries.py` | 433-450 | Replace 2× `rx.input` with `rx.select` + popover; update heading labels to "Inicio (DD/MM/AAAA)" |
| `kakumi_app/states/tournament_crud_state.py` | multiple | Add `_iso_to_display()`, `_display_to_date()` helpers; update `set_form_values` to convert ISO→DD/MM/YYYY; update `save_tournament` parse format; update `_serialize_tournament` to include formatted display keys |
| `kakumi_app/components/date_calendar.py` | **new file** | Pure Reflex calendar popover: `rx.grid` month grid, `rx.button` day cells, prev/next month nav, DD/MM/YYYY display |

### Test changes

| File | What changes |
|------|-------------|
| `tests/test_crud_registries_apply.py` | ~6 assertions with `"2027-03-01"` → `"01/03/2027"`; 2 assertions checking `row["start_date"] == "2027-04-10"` → formatted value |
| Plus **new TDD test file** | e.g., `tests/test_date_calendar.py` — RED tests for format conversion, parse, component render |

### No changes needed (verified)

| File | Why |
|------|-----|
| `tournament_model.py` | Model stays `datetime.date` |
| `base_crud_state.py` | No date logic |
| `results_service.py` | `str(date)` stays ISO for API payloads |
| `export_service.py` | `.isoformat()` stays ISO for machine export |
| `viewer_state.py` / `viewer_service.py` | `model_dump(mode="json")` stays ISO |
| `conftest.py` | Creates `Tournament(datetime.date(...))` directly |
| Alembic migrations | No schema change |

---

## 4. Risks (8 identified)

| # | Risk | Likelihood | Mitigation |
|---|------|-----------|------------|
| R1 | ISO→DD/MM/YYYY conversion failure in `set_form_values` | Medium | Add robust `_iso_to_display()` with fallback |
| R2 | Test assertions with old format fail | **Certain** | Bulk update all test strings; run full suite |
| R3 | `set_form_values` feeds ISO but UI expects DD/MM/YYYY | **Certain** | Must add conversion step |
| R4 | DD-MM-YYYY variant parsing | Low | `.replace("-", "/")` before `strptime` |
| R5 | Calendar component has no precedent in codebase | Medium | Start minimal; defer edge cases to spec |
| R6 | `rx.popover` may not exist in Reflex 0.8.28 | Medium | Fallback: `rx.dialog` or custom absolute overlay |
| R7 | Date range validation opportunity | Low (opportunity) | Defer to follow-up |
| R8 | Mobile touch targets | Low | Use responsive sizing, min 44px targets |

**Key blocking question**: Does Reflex 0.8.28 expose `rx.popover`? The codebase already uses `rx.dialog.root` (sidebar, kumite scoreboard). If `rx.popover` is unavailable, the calendar overlay can be built as a positioned `rx.box` toggled by `rx.cond`.

---

## 5. Prior Art (Existing Component Patterns)

| Component | Pattern | Lesson for calendar |
|-----------|---------|-------------------|
| `sidebar.py` | `rx.dialog.root` → `rx.dialog.content` | Radix Dialog works in 0.8.28 — popover fallback proven |
| `kata_scoreboard.py` | `rx.select(items, value=, on_change=)` | Standard dropdown pattern for trigger |
| `kata_scoreboard.py` | `rx.cond(cond, then, else)` | Conditional visibility toggle for overlay |
| `registry_crud.py` | Pure function returning `rx.Component` | Calendar component follows same pattern |
| No calendar component exists | — | First one, sets the pattern |

---

## 6. Change Boundaries

```
┌──────────────────────────────────────────────────────────┐
│                     IN SCOPE                              │
│  registries.py  │  tournament_crud_state.py  │  NEW       │
│  (UI form)      │  (parse + format helpers)  │  calendar  │
│  + table display│  + set_form_values fix     │  component │
│  + tests        │  + save_tournament parse   │            │
└──────────────────────────────────────────────────────────┘
         OUT OF SCOPE (intentionally excluded)
         Model  │  Services  │  Export  │  Viewer
         (nocfg)│  (keep ISO)│ (keepISO)│ (keep ISO)
```

---

## 7. Dependency Graph

No new external dependencies. Internal dependencies:

```
date_calendar.py (new)
    └── depends on: Reflex rx.grid, rx.button, rx.text, rx.hstack
    └── consumed by: registries.py _tournament_form()

tournament_crud_state.py (modified)
    └── new methods:
        └── _iso_to_display(iso_str: str) → str
        └── _display_to_date(display_str: str) → datetime.date | None
        └── _date_to_iso(d: datetime.date) → str
    └── modified methods:
        └── set_form_values() — ISO→display conversion
        └── save_tournament() — parse DD/MM/YYYY
        └── _serialize_tournament() — add start_date_display / end_date_display

tests/test_date_calendar.py (new, TDD RED)
    └── test_iso_to_display_conversion()
    └── test_display_to_date_accepts_slash()
    └── test_display_to_date_accepts_dash()
    └── test_display_to_date_rejects_garbage()

tests/test_crud_registries_apply.py (modified)
    └── update all date string assertions
```

---

## 8. Verdict: ✅ Proceed

This is a **well-contained UI+state change** with clearly defined boundaries:

- **3 existing files** modified, **1 new file** created
- **0 new external dependencies**
- **0 DB migrations**
- **8 risks** — all have mitigations; none are blockers
- **TDD-compatible** — focused RED tests for parse/format helpers, existing tests updated

### Decision needed before spec phase

**Popover mechanism**: Does this Reflex 0.8.28 project have `rx.popover` available, or should we fall back to `rx.dialog` or a positioned `rx.cond` overlay? This affects the calendar component architecture but not the scope or risk profile.

### Recommendation

Add `start_date_display` / `end_date_display` keys in `_serialize_tournament()` so the table can show DD/MM/YYYY without touching service-layer ISO format.

---

*Note: I don't have a write tool available in this session, so the exploration.md file could not be written to `/tmp/pi-subagents-uid-1000/chain-runs/4f17a0a8/exploration.md`. The progress.md also could not be updated. The full exploration content is delivered above.*