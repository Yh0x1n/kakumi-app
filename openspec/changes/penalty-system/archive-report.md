# Archive Report: penalty-system

## Status: ARCHIVED
## Date: 2026-04-18
## Verification: PASS (316 passed, 1 skipped)

## Summary
Implemented complete WKF 2026 penalty system for Kumite matches including Chui/Hansoku Chui/Hansoku/Shikkaku escalation, Round-Robin Shikkaku handling with last-bout/non-last-bout differentiation, scheduling overlap enforcement (one athlete per tatami), concurrent penalty protection with DB locking, and `remove_last_penalty` guard for IN_PROGRESS matches only.

## Artifacts
- proposal.md
- spec.md
- design.md
- tasks.md (27/27 complete)
- verify-report.md
- archive-report.md (this file)

## Files Implemented

### Models & Migrations
- `kakumi_app/models/athlete_model.py` — Added `is_disqualified: bool`
- `kakumi_app/models/tournament_model.py` — Added `scheduling_gap_seconds: int = 75`, `StandingsDeltaLog` model, indices
- `alembic/versions/b1f4a2d9c8e1_add_penalty_system_fields.py` — Migration for columns, table, indices

### Services
- `kakumi_app/services/exceptions.py` — Created: `PenaltyError`, `MatchNotInProgressError`, `ConcurrencyError`, `PenaltyRemovalNotAllowedError`, `ShikkakuRoundRobinError`, `AthleteSchedulingConflictError`, `PenaltyEscalationError`
- `kakumi_app/services/scheduling_service.py` — Created: `check_athlete_scheduling_overlap()`
- `kakumi_app/services/kumite_scoring_service.py` — Modified: escalation logic, `with_for_update()` + retries, `_apply_shikkaku_round_robin()`, `_is_last_rr_match()`, `_nullify_rr_previous_scores()`, `_cancel_remaining_rr_matches()`, `_capture_standings_delta()`, `_persist_standings_delta()`, `revert_shikkaku()`, `remove_last_penalty()`

### State (Reflex)
- `kakumi_app/states/kumite_match_state.py` — Created: `KumiteMatchState(rx.State)` with timer pause/sync, penalty handlers

### Tests
- `tests/test_penalty_foundations.py` — Model and exception tests
- `tests/test_penalty_migrations.py` — Schema and index tests
- `tests/test_kumite_penalty_service.py` — Escalation and match-end tests
- `tests/test_shikkaku_round_robin.py` — RR last/non-last, individual/team
- `tests/test_scheduling_overlap.py` — Overlap detection, gap window
- `tests/test_penalty_removal.py` — Guard clause, de-escalation
- `tests/test_revert_shikkaku.py` — Snapshot, revert, penalty deletion
- `tests/test_kumite_match_state.py` — Reflex state tests
- `tests/test_penalty_system_integration.py` — Spec scenarios 1–8
- `tests/test_penalty_concurrency.py` — Lock contention (SQLite)
- `tests/conftest.py` — Shared fixtures for RR, team, tatami, PostgreSQL markers

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|---|
| Penalty table | Reuse existing `Penalty` model | Avoids destructive migration |
| DQ flag | `is_disqualified: bool` on `Athlete` | Simple, queryable, matches spec |
| Concurrency | `with_for_update()` + exponential backoff (3 retries) | SQLite dev: serialized txn; PG prod: real row lock |
| Timer sync | Frontend pauses → backend confirms `match_time_seconds` | Reflex round-trip state var per RNF-04 |
| SHIKKAKU last bout | Preserve prior scores; non-last: nullify | WKF Art. 10.7.2 |
| SHIKKAKU individual vs team | Bifurcate per `category.modality` | WKF 3.7.3 |
| Scheduling overlap check | NEW `scheduling_service.py`, called before penalty write | Service-layer guard catches conflicts at penalty entry point |
| Rollback mechanism | `StandingsDeltaLog` table for admin revert | Audit trail for massive SHIKKAKU impact |

## TDD Audit Trail

| Batch | Tasks | RED | GREEN | REFACTOR | Safety Net |
|-------|-------|-----|-------|----------|------------|
| 1 | TASK-1..6 | ✅ Model/migration tests first | ✅ All tests pass | ✅ Defaults, downgrade | ✅ Existing tests baseline |
| 2 | TASK-7..9 | ✅ Escalation tests first | ✅ Service impl | ✅ Extract helpers | ✅ Full suite passes |
| 3 | TASK-10..12 | ✅ RR Shikkaku tests first | ✅ RR helpers | ✅ WKF note format | ✅ Full suite passes |
| 4 | TASK-13..15 | ✅ Scheduling tests first | ✅ New service | ✅ Overlap math | ✅ Full suite passes |
| 5 | TASK-16..18 | ✅ Removal guard tests | ✅ Guard + de-escalate | ✅ Extract helpers | ✅ Full suite passes |
| 6 | TASK-19..21 | ✅ Revert/snapshot tests | ✅ Delta log + revert | ✅ Dedupe serialization | ✅ Full suite passes |
| 7 | TASK-22..24 | ✅ Reflex state tests | ✅ KumiteMatchState | ✅ State mapping | ✅ Full suite passes |
| 8 | TASK-25..27 | ✅ Integration tests | ✅ Fixtures + markers | ✅ Dedupe fixtures | ✅ Full suite passes |
| Hotfix | Fix-1, Fix-2 | ✅ Revert penalty-row test | ✅ Service update | ✅ Ruff clean | ✅ Triangulation (pre/post) |

**Known TDD Gap**: Per-task RED/GREEN evidence for TASK-1..27 not fully recorded in apply-progress artifact. Post-verify hotfix has explicit triangulation evidence.

## Known Limitations

- **PostgreSQL concurrency test skipped**: Real concurrent write contention requires actual Postgres; SQLite test uses serialized txn (no actual lock). CI with Postgres needed for production guarantee.
- **TDD audit trail partial for TASK-1..24**: Result-level only, not per-task RED/GREEN evidence in apply-progress artifact.
- **No E2E tests**: Frontend UI flows not covered; only Reflex state layer tested.
- **`MatchStatus.CANCELLED` stored as string**: Enum value not defined; plain string used in `notes` field for cancelled RR matches.
- **No migration index existence tests**: Tests verify columns/tables exist but not index creation (`ix_penalties_match_participant`, `ix_matches_tatami_start_time`).

## Next Recommended Changes

1. **Standardize async tests to `@pytest.mark.anyio` only** — Current mix of `pytest-asyncio` and `anyio` causes marker conflicts in some test files.
2. **Add migration index tests** — Assert `ix_penalties_match_participant` and `ix_matches_tatami_start_time` exist after migration.
3. **Add `MatchStatus.CANCELLED` enum value** — Currently stored as plain string; should be proper enum member.
4. **Create main spec for `kumite-penalty-system`** — Penalty system introduces NEW capability not covered by existing main specs. Consider `openspec/specs/kumite-penalty-system/spec.md` to capture requirements for future changes.
5. **Replay test suite with PostgreSQL CI** — Validate real concurrent contention behavior before production deployment.

## Specs Synced

**No main specs updated** — The penalty-system change introduces NEW capabilities (`kumite-penalty-system`, `match-state-management`) that don't have corresponding main spec files in `openspec/specs/`. Existing specs (`tournament-state-transitions`, `tournament-state-validation`) are tournament-level and don't require updates from this match-level change.

**Recommendation**: Create `openspec/specs/kumite-scoring-system/spec.md` to capture the penalty rules for future changes.

## Verification Summary

| Check | Result |
|-------|--------|
| Test suite | 316 passed, 1 skipped (PostgreSQL marker) |
| Task completion | 27/27 ✅ |
| Spec scenarios | 8/8 PASS |
| Design compliance | 8/8 PASS |
| WKF compliance | 3/3 PASS |
| Ruff (penalty-system files) | CLEAN |
| CRITICAL | none |
| WARNING | TDD audit trail partial |

---

*Archive completed: 2026-04-18*
*Change: penalty-system*
*Verification: PASS*