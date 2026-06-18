# Proposal: Judge Panel Validation Warning on Category Form

## Intent

When an operator creates or edits a kata category, the `judge_panel_size` selector (3, 5, or 7) can be set to a value that exceeds the number of referees actually registered in the system. When the match later tries to load judges at competition time, it fails silently or shows "Panel de jueces no disponible" because there aren't enough referee records to fill the panel slots.

This proposal adds a lightweight, real-time, non-blocking warning on the category form that shows the operator how many referees exist vs. how many the panel requires — before they save the category.

## Scope

### In Scope

- A new `_referee_count` state variable in `TournamentCategoryState` (int, default 0)
- A new `_load_referee_count()` method that queries `count(Referee)` from the DB
- A new `set_judge_panel_size()` modification to also call `_load_referee_count()` after updating the value
- A reactive `judge_panel_warning` computed var (`@rx.var`) that returns the localized warning string (or empty string) when `form_judge_panel_size` > `_referee_count`
- UI: a small inline `rx.text` element, rendered only when the warning is active, placed immediately after the `judge_panel_size` select inside the kata-conditional block
- The warning MUST appear both when **creating** a new category and when **editing** an existing one
- The warning MUST update reactively when the panel size dropdown changes (DB query on every `on_change`)
- The warning MUST **not** block form submission — it is purely advisory

### Out of Scope

- No changes to `kata_match_state.py` match loader judge restriction (noted as a separate concern for later)
- No changes to `kata_decision_rule` or `scoring_type` / `kata_flow_mode` behavior
- No changes to the `Referee` model or how judges are assigned at match time
- No permission or role-based gating of the warning
- No blocking save logic

## Acceptance Criteria

1. **Warning visible on create**: When creating a kata category, if `judge_panel_size` > count of all `Referee` records in the DB, a warning line appears below the panel size select.
2. **Warning visible on edit**: Same behavior when editing an existing kata category and the condition holds.
3. **Reactive update**: Changing the dropdown value fires a DB query and updates the warning in real-time.
4. **No false positives for kumite**: When modality is kumite (kata fields hidden), no warning is shown.
5. **No blocking**: The operator can save the category regardless of the warning state.
6. **Warning text**: `"Jueces disponibles: X. Panel requiere: Y."` (localized in Spanish).
7. **Inline placement**: Small text, warning color, directly below the judge_panel_size select.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `kakumi_app/states/tournament_category_state.py` | Modified | Add `_referee_count`, `_load_referee_count()`, `judge_panel_warning` rx.var, update `set_judge_panel_size()` |
| `kakumi_app/pages/tournament.py` | Modified | Add inline warning `rx.text` in `_categories_card()` kata fields block |
| `tests/test_tournament_category_state.py` | Modified | Test warning logic, reactivity, no effect on save |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| DB query on every dropdown change creates latency | Low | Query is a simple `count(*)` on a small table; imperceptible |
| Warning flashes on load before count resolves | Low | Default `_referee_count = 0` will show warning briefly; trivial edge case |
| Existing tests break if they expect no DB interaction on dropdown change | Low | Update affected test assertions; the handler is lightweight |

## Rollback Plan

Single commit. `git revert <commit-hash>` removes the warning with no side effects on category CRUD behavior.

## Dependencies

- `Referee` model (`kakumi_app/models/referee_model.py`) must exist (it does)
- `rx.session()` query context available (already used throughout the state)

## Success Criteria

- [ ] Manual: Open category creation form for kata modality → set panel size to 7 → verify warning appears when fewer than 7 referees exist
- [ ] Manual: Change panel size to 3 → verify warning disappears (or shows only if <3 referees)
- [ ] Manual: Save category with warning active → verify save succeeds
- [ ] Manual: Edit existing kata category with same conditions → warning behaves identically
- [ ] `python -m pytest tests/test_tournament_category_state.py -v` → all green
- [ ] `python -m pytest tests/ -v` → no regressions
