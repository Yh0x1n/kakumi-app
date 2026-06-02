# Apply Progress — disconnected-client-warnings (Phase 1)

Date: 2026-06-02
Mode: strict TDD

## Preconditions / Artifact Readout

- `openspec/config.yaml` found and read (`strict_tdd: true`, pytest runner).
- Change-local artifacts expected by phase (`proposal.md`, `spec.md`, `design.md`, `tasks.md`) were **not present** under `openspec/changes/disconnected-client-warnings/` at apply start.
- Implemented directly from parent-provided Phase1 scope for disconnected-client-warnings.

## Completed Tasks

- [x] `SecondaryDisplayState`:
  - [x] Set `viewer_heartbeat_ttl_seconds = 5`.
  - [x] Added in-lock connection re-check in `poll_snapshot_loop` before snapshot mutation.
  - [x] Preserved heartbeat registration/touch behavior.
- [x] `KataMatchState`:
  - [x] Added `_is_viewer_connected()` using token manager socket probe with exception fallback to `True`.
  - [x] Guarded `_publish_display_snapshot()` to skip publish when disconnected.
- [x] `KumiteMatchState`:
  - [x] Guarded `_publish_display_snapshot()` to skip publish when disconnected.
  - [x] Added in-lock connection re-checks in `run_timer_loop` before timer mutation, snapshot prep, and lock-scoped status updates.
  - [x] On in-lock disconnect, set `timer_running=False` and `_timer_loop_active=False` then break.
- [x] Tests:
  - [x] Added `test_poll_snapshot_loop_skips_mutation_when_disconnected_during_lock`.
  - [x] Added `test_reduced_heartbeat_ttl_allows_normal_polling`.
  - [x] Added `test_publish_display_snapshot_skipped_when_viewer_disconnected` (Kata).
  - [x] Added `test_run_timer_loop_checks_connection_inside_lock`.
  - [x] Added `test_publish_display_snapshot_skipped_when_viewer_disconnected` (Kumite).
  - [x] Triangulation assertions added to confirm no disconnected snapshot writes and no state mutation race side effects.

## Files Changed

- `kakumi_app/states/secondary_display_state.py`
- `kakumi_app/states/kata_match_state.py`
- `kakumi_app/states/kumite_match_state.py`
- `tests/test_secondary_display_state.py`
- `tests/test_kata_match_state.py`
- `tests/test_kumite_match_state.py`

## Test Commands Run

1. RED (expected failures before implementation complete)

```bash
pytest -q tests/test_secondary_display_state.py tests/test_kata_match_state.py tests/test_kumite_match_state.py
```

Result: **failed** (`6 failed, 98 passed`) — failures included missing Kata/Kumite publish guards and missing Kumite in-lock timer-loop disconnect handling.

2. GREEN (after implementation)

```bash
pytest -q tests/test_secondary_display_state.py tests/test_kata_match_state.py tests/test_kumite_match_state.py
```

Result: **passed** (`104 passed`).

3. TRIANGULATE/REFACTOR verification reruns

```bash
pytest -q tests/test_secondary_display_state.py tests/test_kata_match_state.py tests/test_kumite_match_state.py
```

Result: **passed** (`104 passed`).

## TDD Cycle Evidence

| Task Slice | RED evidence | GREEN evidence | TRIANGULATE evidence | REFACTOR evidence |
|---|---|---|---|---|
| Secondary display TOCTOU + TTL | Initial focused run failed in secondary coverage before full completion; added race + TTL tests | Focused suite passed after TTL=5 and in-lock recheck path aligned (`104 passed`) | Added assertions verifying snapshot/modality/source_kind are unchanged when disconnect occurs during lock | Kept heartbeat behavior intact; added targeted comments for TOCTOU intent |
| Kata publish guard | RED: publish-when-disconnected test failed (`publish_calls` non-empty) | GREEN: publish skipped when disconnected (`publish_calls == []`) | Added assertion that `public_display_key` remains stable and no publish side effects occur | Added explicit guard comment in `_publish_display_snapshot()` |
| Kumite timer-loop in-lock check + publish guard | RED: in-lock disconnect test failed (snapshot was published / timer mutated) | GREEN: no publish + no timer decrement on inside-lock disconnect | Added assertions for no extra mutation (`last_action_label` unchanged) and stable display state | Extracted `_mark_timer_loop_disconnected()` helper and documented in-lock TOCTOU recheck |

## Deviations / Notes

- Additional type/lint cleanups were required in touched files due pre-existing static-analysis blockers (event callback `.fn` typing in tests, Optional/union/type narrowing cleanup in state files).
- No product/API behavior changes beyond Phase1 disconnected-client safeguards.

## Remaining Tasks

- Phase1 scope from parent prompt is complete.
- Remaining work (if any) belongs to later phases of `disconnected-client-warnings`.

## Workload / PR Boundary

- Boundary delivered: **Phase1 only** (TOCTOU close + operator-side publish guards + focused tests).
- Change volume is above the 400-line review budget because touched test modules required local typing/compatibility cleanups alongside Phase1 behavior changes.
