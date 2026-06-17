## Design

**Change**: fix-kata-tournament-flow-v2

### Overview

Three independent fixes in a single change: (A) calendar buttons default to `type="submit"` inside `rx.form`, (B1) kata category form missing 4 existing model fields, (B2) bracket generation incorrectly creates `Match` records for INFORMAL kata categories.

---

## Problem A — Calendar Submit Fix

**Root cause**: `rx.button` defaults to `type="submit"` in HTML. When `date_calendar_popover()` renders inside `rx.form` (registries.py), clicking any day cell, month nav arrow, or the trigger button submits the enclosing form.

**Fix**: Add `type="button"` to 3 `rx.button` calls in `date_calendar.py`:

| Line | Button | Change |
|------|--------|--------|
| ~28 | `_render_day_cell` day button | `type="button"` |
| ~78 | `‹` prev month nav | `type="button"` |
| ~88 | `›` next month nav | `type="button"` |
| ~148 | trigger button (already not in form context, but add for consistency) | `type="button"` |

**Pattern**: `rx.button("text", type="button", ...)`. No state changes needed.

**Files**: `kakumi_app/components/date_calendar.py` — 4 lines changed.

---

## Problem B1 — Category Form Fields

**Root cause**: `TournamentCategory` model has `judge_panel_size`, `kata_flow_mode`, `scoring_type`, and `kata_decision_rule` fields, but the category form in `_categories_card()` does not render them. Creating/editing a kata category silently drops these values.

**Fix**: Add 3 form fields wrapped in `rx.cond(modality == "Kata Individual" or modality == "Kata por Equipos")`.

### Form Fields

```
1. judge_panel_size: rx.select(["3", "5", "7"])
   └─ Expands range from 3..5 to 3..7 (WKF 2026 allows 7-judge panels)

2. kata_flow_mode: rx.select(["STANDARD", "INFORMAL"])
   └─ Determines match generation strategy

3. scoring_type: rx.cond(
     kata_flow_mode == "INFORMAL",
     rx.text("INFORMAL (automático)"),  # hidden auto-set
     rx.select(["average-with-discard", "majority-by-judge"])
   )
```

### State Changes (`tournament_category_state.py`)

**New form vars** (3 additional attrs matching existing pattern):
| Var | Type | Default |
|-----|------|---------|
| `form_judge_panel_size` | `str` | `"3"` |
| `form_kata_flow_mode` | `str` | `"STANDARD"` |
| `form_scoring_type` | `str` | `"average-with-discard"` |

Wait — the state already has `judge_panel_size` etc as model field names. But the state uses simple field names like `name`, `modality`, `gender` etc. So the new vars should follow the same pattern: `judge_panel_size`, `kata_flow_mode`, `scoring_type`.

**New event handlers**:
- `set_judge_panel_size(value: str)` — like `set_bracket_size`
- `set_kata_flow_mode(value: str)` — also resets scoring_type to default when STANDARD/INFORMAL toggles
- `set_scoring_type(value: str)` — like `set_competition_system`

**Modified methods**:

| Method | Change |
|--------|--------|
| `reset_form()` | Reset 3 new fields to defaults |
| `_validate_form()` | Validate judge_panel_size ∈ {"3","5","7"}, kata_flow_mode ∈ {"STANDARD","INFORMAL"}, scoring_type ∈ {"average-with-discard","majority-by-judge","INFORMAL"} |
| `_serialize_category()` | Map model fields to display values for the table |
| `set_form_values()` | Load these fields when editing an existing category |

### Model Changes (`tournament_model.py`)

| Change | Detail |
|--------|--------|
| `judge_panel_size` comment | `# 3..5` → `# 3..7` |
| `flag_count` field | Remove the field entirely (was `Optional[int]`, unused in code) |

No migration needed — `flag_count` is already nullable with `default=None`, and removing a SQLModel field that never contained meaningful data is safe. Existing rows keep the column; SQLModel stops mapping it.

---

## Problem B2 — INFORMAL Bracket Guard

**Root cause**: `_generate_brackets_for_tournament()` iterates all categories and calls `generate_bracket()` for ELIMINATION/ROUND_ROBIN systems. INFORMAL kata categories should NOT get Match records — performances are created manually via `KataInformalService.save_performance()`.

**Fix**: Add guard at top of category loop in `_generate_brackets_for_tournament()`:

```python
for category in categories:
    # Skip INFORMAL kata categories — they use manual performance flow
    if getattr(category, "kata_flow_mode", "STANDARD") == "INFORMAL":
        continue
    if category.competition_system not in { ... }:
        continue
    ...
```

`getattr(..., "STANDARD")` handles both existing DB rows (before `kata_flow_mode` was added to model) and new categories.

**Files**: `kakumi_app/services/tournament_service.py` — 3 lines added.

No changes to `bracket_service.py` or `kata_informal_service.py`.

---

## Architecture Decisions

### 1. `rx.cond` vs separate form for kata vs kumite

**Decision**: `rx.cond` inside `_categories_card()`.

**Why**: The kata fields are always visible when modality is kata, hidden otherwise. A separate form component would duplicate ~80% of the existing form structure. `rx.cond` follows the existing pattern used throughout the file (e.g., lifecycle buttons in `_lifecycle_card`). No state duplication, no new component files.

**Tradeoff**: The template file gets slightly longer. Acceptable — 3 `rx.cond` blocks at ~6 lines each is negligible.

### 2. Skip bracket gen vs remove existing matches

**Decision**: Only prevent NEW `Match` records from being created.

**Why**: Backward compatibility. An operator who already ran `transition_to(EN_CURSO)` on a tournament with INFORMAL categories may have existing Match records. Deleting them would be destructive and surprising. The guard only prevents future bracket generation. The `_validate_finalizado` method already handles INFORMAL categories by checking `KataInformalPerformance` status, not Match records — so existing Match records don't block finalization.

**Cost**: Old Match records remain as orphans. Acceptable — they're read-only and never interfere. Manual cleanup via DB console if desired.

### 3. Model-only `flag_count` removal

**Decision**: Remove from model, no migration.

**Why**: The field is `Optional[int]` with `default=None` and zero references in production code. SQLModel simply stops mapping the column. The column stays in the DB table but is invisible to the ORM. This is safe, reversible (add field back), and avoids an unnecessary Alembic revision.

**Risk**: If any raw SQL query references `flag_count`, it will still work. Python code accessing `category.flag_count` will raise `AttributeError` — grep shows zero usages.

### 4. No auto-draw for INFORMAL round-robin

**Decision**: Out of scope per proposal.

**Why**: INFORMAL flow uses the existing `KataInformalService.save_performance()` manual workflow. Operators create performances one by one. Automating round-robin draw (pairings, schedule) would require a separate feature with its own proposal. This change only prevents accidental `Match` generation — it does not add new capability.

**Relationship to existing code**: `KataInformalService` already queries `Match` records for victory-point aggregation (line ~42-66) and head-to-head resolution (line ~69-105). If a category somehow has Match records, the service works correctly. The guard prevents NEW matches from being created, so over time INFORMAL categories will have zero matches (clean state).

---

## Testing Strategy

### Unit Tests

| Test | What | File |
|------|------|------|
| `test_validate_form_kata_fields` | `_validate_form()` succeeds with valid kata fields, fails with invalid judge_panel_size | `test_tournament_category_state.py` |
| `test_serialize_category_kata` | `_serialize_category()` includes judge_panel_size, kata_flow_mode, scoring_type | same |
| `test_bracket_guard_informal` | `_generate_brackets_for_tournament()` skips INFORMAL categories | `test_tournament_service.py` |
| `test_bracket_guard_standard` | STANDARD categories still generate brackets | same |

### Integration/Smoke

- Create kata category with all new fields → verify DB row has correct values
- Edit kata category → verify field pre-fill
- Transition to EN_CURSO → verify INFORMAL categories get zero new `Match` rows
- Transition to EN_CURSO → verify STANDARD categories get brackets as before

### Manual

- Click calendar day in tournament create form → verify form does NOT submit
- Click month nav arrows → verify form does NOT submit

---

## Files Affected

| File | Change | Lines |
|------|--------|-------|
| `kakumi_app/components/date_calendar.py` | 4x `type="button"` | +4 |
| `kakumi_app/pages/tournament.py` | 3 kata fields in `_categories_card()` | +~30 |
| `kakumi_app/states/tournament_category_state.py` | 3 vars, 3 setters, reset/validate/serialize changes | +~40 |
| `kakumi_app/models/tournament_model.py` | `judge_panel_size` comment; remove `flag_count` | -2, ~1 |
| `kakumi_app/services/tournament_service.py` | INFORMAL guard in `_generate_brackets_for_tournament()` | +3 |

**Total**: 5 files modified, ~75 lines added, ~2 removed. Zero new files.
