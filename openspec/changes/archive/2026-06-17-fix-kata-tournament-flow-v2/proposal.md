# Proposal: Fix Kata Tournament Flow v2

## Intent

Two bugs in the tournament workflow: (A) calendar date picker inside `rx.form` triggers unintended form submit because `rx.button` lacks `type="button"`; (B) kata category creation omits 4 existing model fields (B1), and bracket generation incorrectly creates Match records for INFORMAL categories (B2).

## Scope

### In Scope
1. **Problem A** — Add `type="button"` to 3 `rx.button` calls in `date_calendar.py`
2. **Problem B1** — Add `judge_panel_size`, `kata_flow_mode`, `scoring_type` fields to category form (visible only when modality = kata), plus validation + serialization in state layer
3. **Problem B1 model fix** — Update `judge_panel_size` comment range 3..5 → 3..7; clean up `flag_count` from model (unused)
4. **Problem B2** — Skip INFORMAL categories in `_generate_brackets_for_tournament()`

### Out of Scope
- INFORMAL round-robin draw automation (performances created manually by operator, as currently implemented)
- Model migrations (fields already exist in DB; `flag_count` removal is model-only, no migration needed)
- Kumite-specific form fields (none added)

## Capabilities

### New Capabilities
None — pure bugfix + form extension. No new spec-level behavior introduced.

### Modified Capabilities
None — existing specs (`tournament-state-transitions`, etc.) unchanged. B2 corrects bracket generation to match the implicit contract: INFORMAL categories never produce Match records.

## Approach

| Bug | Fix | Risk |
|-----|-----|------|
| A | `type="button"` on 3 buttons in `date_calendar.py` | Zero |
| B1 | 4 form fields + state setters + `_validate_form()` / `_serialize_category()` + conditional render via `rx.cond(modality == kata)` | Low |
| B1 model | Comment range 3..5 → 3..7; remove `flag_count` field | Low |
| B2 | Add `kata_flow_mode != INFORMAL` guard in `_generate_brackets_for_tournament()` | Low |

## Affected Areas

| File | Impact | Description |
|------|--------|-------------|
| `kakumi_app/components/date_calendar.py` | Modified | 3x `type="button"` added (Problem A) |
| `kakumi_app/pages/tournament.py` | Modified | 4 kata-specific form fields in `_categories_card()` (B1) |
| `kakumi_app/states/tournament_category_state.py` | Modified | Setters, `reset_form()`, `_validate_form()`, `_serialize_category()` for new fields (B1) |
| `kakumi_app/models/tournament_model.py` | Modified | `judge_panel_size` comment fix; remove `flag_count` (B1 model) |
| `kakumi_app/services/tournament_service.py` | Modified | Bracket gen guard for INFORMAL (B2) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing categories with default STANDARD flow break | Low | Default `kata_flow_mode = STANDARD` — backward compatible |
| `flag_count` removal causes import error | Low | Field is `Optional[int]` with `default=None`; unused in code |
| INFORMAL category with existing Match records | Low | B2 only prevents NEW bracket gen; existing data unaffected |

## Rollback Plan

Revert each file individually. No data migration involved. For B2, regenerate brackets after revert by re-running `transition_to(EN_CURSO)`.

## Dependencies

None.

## Success Criteria

- [ ] Calendar picker no longer triggers `save_tournament` on day click
- [ ] Category form shows 4 kata fields only when modality = kata
- [ ] Creating/editing a kata category persists `judge_panel_size`, `kata_flow_mode`, `scoring_type`
- [ ] INFORMAL categories have zero Match records after `transition_to(EN_CURSO)`
- [ ] STANDARD categories unaffected (brackets generated as before)
