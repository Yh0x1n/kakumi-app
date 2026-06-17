# Tasks: fix-kata-tournament-flow-v2

## Dependency Graph

```
Phase 1 (model) ──┐
                   ├──► Phase 3 (state) ──► Phase 4 (form)
Phase 2 (calendar) ──┘                        │
                                              ├──► Phase 5 (bracket guard)
                                              │
                                              └──► Phase 6 (tests)
                                                       │
                                                       └──► Phase 7 (verify existing)
```

No hard dependencies between phases 1/2 — can run in parallel. Phase 3 depends on phase 1 (model changes). Phases 4-5 depend on 3. Phase 6 depends on 4-5. Phase 7 is final.

---

## Phase 1 — Model fix (tournament_model.py)

**File**: `kakumi_app/models/tournament_model.py`

| # | Task | Detail | Lines |
|--|------|--------|-------|
| [x] 1.1 | Fix `judge_panel_size` comment | `# 3..5` → `# 3..7` | 1 |
| [x] 1.2 | Remove `flag_count` field | Delete the `flag_count: Optional[int]` line entirely | -1 |

**Dependencies**: None.

**Verification**: `grep -r "flag_count" kakumi_app/` returns zero matches (outside this field definition).

---

## Phase 2 — Calendar submit fix (date_calendar.py)

**File**: `kakumi_app/components/date_calendar.py`

| # | Task | Detail | Lines |
|--|------|--------|-------|
| [x] 2.1 | Add `type="button"` to day cell button | `_render_day_cell` — `rx.button(..., type="button")` | +1 |
| [x] 2.2 | Add `type="button"` to prev month nav | `rx.button("‹", ..., type="button")` | +1 |
| [x] 2.3 | Add `type="button"` to next month nav | `rx.button("›", ..., type="button")` | +1 |
| [x] 2.4 | Add `type="button"` to trigger button | `rx.button(..., type="button")` on trigger | +1 |

**Dependencies**: None (parallel with phase 1).

**Pattern**: `rx.button(..., type="button")` — 4 lines, zero state changes.

---

## Phase 3 — Category state (tournament_category_state.py)

**File**: `kakumi_app/states/tournament_category_state.py`

| # | Task | Detail | Lines |
|--|------|--------|-------|
| [x] 3.1 | Add 3 form vars | `form_judge_panel_size: str = "3"`, `form_kata_flow_mode: str = "STANDARD"`, `form_scoring_type: str = "average-with-discard"` | 3 |
| [x] 3.2 | Add 3 setter handlers | `set_judge_panel_size`, `set_kata_flow_mode` (also resets scoring_type on INFORMAL/STANDARD toggle), `set_scoring_type` | ~12 |
| [x] 3.3 | Modify `reset_form()` | Reset new vars to defaults | +3 |
| [x] 3.4 | Modify `_validate_form()` | Validate judge_panel_size ∈ {"3","5","7"}, kata_flow_mode ∈ {"STANDARD","INFORMAL"}, scoring_type ∈ {"average-with-discard","majority-by-judge","INFORMAL"} | ~15 |
| [x] 3.5 | Modify `_serialize_category()` | Include judge_panel_size, kata_flow_mode, scoring_type in returned dict | +3 |
| [x] 3.6 | Modify `set_form_values()` | Load kata fields when editing existing category | +4 |

**Dependencies**: Phase 1 (model field names must match).

**Validation rules**:
- `judge_panel_size` must be one of "3", "5", "7" — else `"Panel de jueces debe ser 3, 5 o 7"`
- `kata_flow_mode` must be one of "STANDARD", "INFORMAL"
- `scoring_type` must be one of "average-with-discard", "majority-by-judge", "INFORMAL"

**Edge case**: `set_kata_flow_mode("INFORMAL")` auto-sets `scoring_type = "INFORMAL"` and disables the scoring_type selector. Switching back to "STANDARD" resets `scoring_type = "average-with-discard"`.

---

## Phase 4 — Category form fields (tournament.py)

**File**: `kakumi_app/pages/tournament.py` — inside `_categories_card()` after line ~298 (after bracket_size hstack)

| # | Task | Detail | Lines |
|--|------|--------|-------|
| [x] 4.1 | Add `judge_panel_size` rx.select | Wrapped in `rx.cond(modality == "Kata Individual" or modality == "Kata por Equipos")`. Options: ["3", "5", "7"]. | ~8 |
| [x] 4.2 | Add `kata_flow_mode` rx.select | Inside the same rx.cond. Options: ["STANDARD", "INFORMAL"]. | ~8 |
| [x] 4.3 | Add `scoring_type` conditional field | Nested rx.cond: if INFORMAL → disabled text "INFORMAL (automático)", else → rx.select with ["average-with-discard", "majority-by-judge"]. | ~10 |
| [x] 4.4 | Verify auto-lock on INFORMAL scoring | `rx.cond(kata_flow_mode == "INFORMAL", rx.text(...), rx.select(...))` | already counted in 4.3 |

**Dependencies**: Phase 3 (state vars must exist).

**Pattern**: All 3 fields inserted after the bracket_size row (line ~298) in the form vstack, inside `rx.cond(state.modality.is_in(...))`.

---

## Phase 5 — Bracket INFORMAL guard (tournament_service.py)

**File**: `kakumi_app/services/tournament_service.py` — `_generate_brackets_for_tournament()` method (~line 278)

| # | Task | Detail | Lines |
|--|------|--------|-------|
| [x] 5.1 | Add INFORMAL skip guard | Inside `for category in categories:` loop, before the `competition_system` check: `if getattr(category, "kata_flow_mode", "STANDARD") == "INFORMAL": continue` | +3 |

**Dependencies**: None.

**Safety**: `getattr` with default `"STANDARD"` handles legacy rows where `kata_flow_mode` column is NULL.

---

## Phase 6 — Tests

**Files**: `test_tournament_category_state.py`, `test_tournament_service.py`

| # | Task | Detail | Lines |
|--|------|--------|-------|
| [x] 6.1 | Test `_validate_form` kata fields | Valid judge_panel_size=5 succeeds; invalid judge_panel_size=2 fails; valid kata_flow_mode; invalid scoring_type | ~20 |
| [x] 6.2 | Test `_serialize_category` kata | Verify returned dict includes judge_panel_size, kata_flow_mode, scoring_type | ~10 |
| [x] 6.3 | Test bracket guard INFORMAL | `_generate_brackets_for_tournament` skips INFORMAL categories | ~15 |
| [x] 6.4 | Test bracket guard STANDARD | STANDARD categories still generate brackets normally | ~15 |

**Dependencies**: Phases 4-5 (code must exist).

---

## Phase 7 — Verify existing tests pass

| # | Task | Detail |
|--|------|--------|
| [x] 7.1 | Run full test suite | `python -m pytest tests -v` — 880 passed, zero regressions |

**Dependencies**: All prior phases.

---

## Phase 8 — Replace inline kata scoring panel with kata_scoreboard()

**Files**: `kakumi_app/states/kata_match_state.py`, `kakumi_app/pages/competition/category_page.py`, `kakumi_app/states/competition_category_state.py`, `tests/test_kata_match_state.py`

| # | Task | Detail |
|--|------|--------|
| [x] 8.1 | Add `mount_informal_category(category_id)` event to KataMatchState | Sets kata_mode=INFORMAL, is_exhibition=False, loads roster+standings via `_load_informal_session` |
| [x] 8.2 | Add `finalize_category()` event to KataMatchState | Calls `KataInformalService.finalize_category`, sets result/error messages |
| [x] 8.3 | Randomize roster order in `_load_informal_session` | Replace `Athlete.name` with `func.random()` for roster ordering |
| [x] 8.4 | Show only athlete name in roster labels | Modify `informal_roster_labels`, `informal_selected_athlete_label` vars to show name only |
| [x] 8.5 | Fix `select_informal_athlete_from_label` to match by name | Parse roster by name instead of "ID - Name" split |
| [x] 8.6 | Set judge_panel_size from category in `_load_informal_session` | Add `self.judge_panel_size = int(category.judge_panel_size or 5)` |
| [x] 8.7 | Replace inline scoring panel in category_page.py | Remove inline KataInformalState panel, use kata_scoreboard() + "Cerrar categoría" button |
| [x] 8.8 | Update competition_category_state.py chain event | Return `KataMatchState.mount_informal_category(category.id)` instead of `KataInformalState.load_category_session` |
| [x] 8.9 | Write tests for new events and label changes | 12 new tests: mount, finalize, labels by name, select by name, edge cases |

**Dependencies**: Phases 1-7 (existing code must be stable).

---

---

## Phase 9 — Bracket page: show standings for INFORMAL categories

**Files**: `kakumi_app/utils/bracket_utils.py`, `kakumi_app/states/bracket_state.py`, `kakumi_app/pages/competition/bracket_page.py`, `tests/test_bracket_state.py`

| # | Task | Detail | Lines |
|--|------|--------|-------|
| [x] 9.1 | Extend `BracketCategoryData` with `kata_flow_mode` and `standings` | Add 2 optional fields to TypedDict in `bracket_utils.py` | +2 |
| [x] 9.2 | Add `_build_informal_standings()` method to `BracketState` | Static method: queries `KataInformalService.rank_category`, looks up athlete names, builds standings payload | ~25 |
| [x] 9.3 | Populate `kata_flow_mode` and `standings` in `load_bracket()` | Add fields to category dicts, then loop INFORMAL categories to fill standings | +8 |
| [x] 9.4 | Show standings table in `bracket_page.py` for INFORMAL | `rx.cond` branching on `kata_flow_mode`, renders `kata_informal_table` or fallback text | ~10 |
| [x] 9.5 | Write TDD tests for INFORMAL standings in bracket | 4 tests: kata_flow_mode field, empty standings, populated standings, STANDARD unaffected | ~70 |

**Dependencies**: Phases 1-8 (existing code must be stable).

---

---

## Phase 10 — Results page INFORMAL detection + auto-finalize

**Files**: `kakumi_app/services/results_service.py`, `kakumi_app/pages/results.py`, `kakumi_app/states/kata_match_state.py`, `tests/test_results_service.py`, `tests/test_kata_match_state.py`

| # | Task | Detail | Lines |
|--|------|--------|-------|
| [x] 10.1 | Fix `get_category_view()` informal detection | Use `kata_flow_mode == "INFORMAL"` instead of `modality+competition_system` combo | ~5 |
| [x] 10.2 | Enrich informal standings with athlete names | After `rank_category()`, query Athlete table and add `name` + `total_score` keys | ~20 |
| [x] 10.3 | Add `kata_flow_mode` to `category_info` dict | Expose in the result payload for UI display | +1 |
| [x] 10.4 | Improve `category_results()` standings display | Rank emoji (🥇🥈🥉), name, total score badge, VP badge | ~30 |
| [x] 10.5 | Add `is_informal` flag to `get_tournament_view()` | Set `is_informal: bool`, zero match counts for INFORMAL | +4 |
| [x] 10.6 | Update `tournament_results()` for INFORMAL display | Show `podium_status` instead of match progress for INFORMAL | ~6 |
| [x] 10.7 | Auto-finalize after last athlete scored in `_finalize_informal_performance()` | Check `all_scored` after save, call `finalize_category` if complete | ~18 |
| [x] 10.8 | Tests for Phase 10 | 3 new tests: informal detection, auto-finalize, advance-when-more-remain | ~85 |

**Dependencies**: Phases 1-9 (existing code must be stable).

---

---

## Phase 11 — Results hub: show podium names for COMPLETED categories

**Files**: `kakumi_app/services/results_service.py`, `kakumi_app/pages/results.py`, `tests/test_results_service.py`

| # | Task | Detail |
|--|------|--------|
| [x] 11.1 | Enrich `get_tournament_view()` with podium names | Second pass after category_rows: collect athlete IDs, bulk-load names, add `first_place_name`, `second_place_name`, `third_place_display` to each row |
| [x] 11.2 | Show podium in `tournament_results()` | Replace status/progress line with `rx.cond(podium_status=="available")` showing 🥇🥈🥉 names |
| [x] 11.3 | Write tests for podium enrichment | `test_get_tournament_view_returns_podium_names`, `test_get_tournament_view_informal_podium` |

**Dependencies**: Phase 10 (existing results code must be stable).

---

## Summary

| Aspect | Value |
|--------|-------|
| **Total phases** | 11 |
| **Total task items** | 42 |
| **Files modified** | 17 (model, calendar, state, form, service, scoreboard-state, category-page, comp-category-state, tests, bracket-utils, bracket-state, bracket-page, results-service, results-page, kata-match-state, results-service-tests) |
| **New files** | 0 |
| **Test results** | 901 passed, zero regressions |

### Next Step

Ready for **verify** phase (`sdd-verify`).
