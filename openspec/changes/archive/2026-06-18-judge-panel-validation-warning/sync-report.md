# Sync Report — Judge Panel Validation Warning

**Change:** `judge-panel-validation-warning`
**Date:** 2026-06-18
**Syncer:** SDD sync executor

---

## Status: ❌ BLOCKED

The spec delta describes a feature that was reverted during implementation. Syncing it into canonical specs would introduce requirements for a feature that does not exist in the codebase.

---

## Domain: `category-form`

**Spec path:** `openspec/changes/judge-panel-validation-warning/specs/category-form/spec.md`
**Canonical path:** `openspec/specs/category-form/spec.md`

**Delta type:** `## ADDED Requirements`
**Feature described:** Judge Panel Available Referee Warning (`_referee_count`, `_load_referee_count()`, `judge_panel_warning` rx.var, UI warning text)

**Verdict: NOT SYNCED**

### Reason

The verify report (see `verify.md`) confirms:

| Finding | Detail |
|---------|--------|
| Warning feature implementation | **Reverted** — all code removed from source |
| `_referee_count` state var | ❌ Not present in source |
| `_load_referee_count()` method | ❌ Not present in source |
| `judge_panel_warning` rx.var | ❌ Not present in source |
| `func` import from sqlmodel | ❌ Not present in source |
| `Referee` import | ❌ Not present in source |
| UI warning `rx.text` in `tournament.py` | ❌ Not present in source |
| Warning test functions (9) | ❌ Not present in source |
| `"Jueces disponibles"` string | ❌ Not present in source (only in spec/design docs) |

The spec's ADDED requirements describe a feature that was fully reverted. Adding these to the canonical spec would make the spec describe functionality that does not exist, violating the fundamental principle that canonical specs reflect the actual system.

### What Was Actually Delivered

The apply phase changed direction. These two changes were delivered instead (documented in `openspec/changes/judge-panel-validation/apply-progress.md`):

1. **Tournament Status Restriction** — `tournament_category_state.py`
   - `_current_tournament_status: str` state var populated from `tournament.status`
   - `set_form_values()` blocks category form opening when status is EN_CURSO+
   - `save_category()` blocks category create/update when status is EN_CURSO+
   - Allowed statuses: `PLANIFICADO`, `INSCRIPCION`, `VERIFICACION`

2. **Match Loader — No Role Filter** — `kata_match_state.py`
   - Removed `where` clause on referee role: `select(Referee)` loads ALL referees unconditionally

Neither of these changes has a corresponding spec in the `judge-panel-validation-warning` change directory (or anywhere in OpenSpec).

---

## Active Same-Domain Collisions

| Change | Domain | Collision? |
|--------|--------|------------|
| `judge-panel-validation` | (no specs) | No — this change has only `apply-progress.md`, no specs |
| Other active changes | `category-form` | None found in `openspec/changes/` |

No active same-domain collisions detected.

---

## Destructive Sync Assessment

| Check | Finding |
|-------|---------|
| Has REMOVED requirements? | No — delta is only ADDED |
| Has MODIFIED requirements? | No |
| Has large MODIFIED blocks? | No |
| Has RENAMED requirements? | No |
| Sync would make canonical spec incorrect? | **Yes** — would describe a reverted feature |

The ADDED requirements describe a feature that was removed from the codebase. Syncing them would be incorrect.

---

## Validation Checks Performed

1. ✅ Read verify report — confirms warning feature reverted, all code correct
2. ✅ Grepped source for `_referee_count`, `_load_referee_count`, `judge_panel_warning`, `"Jueces disponibles"` — zero matches
3. ✅ Read canonical `specs/category-form/spec.md` — does not contain warning feature requirements
4. ✅ Read `judge-panel-validation/apply-progress.md` — documents actual delivered changes
5. ✅ Checked for same-domain active collisions — none found

---

## Structured Status & Action Context

```json
{
  "changeName": "judge-panel-validation-warning",
  "artifactStore": "openspec",
  "artifacts": {
    "proposal": "present",
    "specs": "present (reverted feature)",
    "design": "present (reverted feature)",
    "tasks": "present (all marked done, feature reverted)",
    "applyProgress": "present (reverted feature)",
    "verifyReport": "present (PASS — code correct, spec mismatch noted)",
    "syncReport": "present (this file)"
  },
  "applyState": "applied-then-reverted",
  "dependencies": {
    "apply": "complete",
    "verify": "pass",
    "sync": "blocked",
    "archive": "blocked (sync must complete first)"
  },
  "actionContext": {
    "mode": "repo-local",
    "workspaceRoot": "/var/home/yhoxr/kakumi-app",
    "allowedEditRoots": ["/var/home/yhoxr/kakumi-app"],
    "warnings": ["Spec describes reverted feature; sync blocked"]
  },
  "blockedReasons": [
    "Spec delta describes ADDED requirements for a feature (warning) that was reverted from the codebase. Syncing would introduce incorrect requirements into canonical specs."
  ]
}
```

---

## Next Recommended Phase

### `sdd-sync` (for `judge-panel-validation` change)

The actual delivered changes (status guards + match loader fix) need proper spec coverage before they can be synced. Recommended sequence:

1. **Create specs** for the actual delivered changes under `openspec/changes/judge-panel-validation/specs/`:
   - `category-form/spec.md` — describe the tournament status restriction guard
   - `match-loader/spec.md` (or add to `category-form`) — describe the no-role-filter match loader change
2. **Update** `openspec/changes/judge-panel-validation/apply-progress.md` to reflect apply completion
3. **Verify** the new specs against code
4. **Sync** the actual delivered specs into canonical

### Regarding this change (`judge-panel-validation-warning`)

After proper specs are created in the other change and synced, archive this change. The spec/design/tasks artifacts describe a reverted feature and should be preserved in archive for audit trail, but not synced into canonical specs.

---

## Supervisor Decision

**Option A confirmed.** Skip sync for this change. The `judge-panel-validation` change documents what was actually delivered. Next step: create proper specs in `judge-panel-validation` and sync from there, then archive this change for audit trail.

> Decision: `sdd-sync` → skipped (not-applicable). Spec describes reverted feature. Actual delivered changes live in `judge-panel-validation` change.
