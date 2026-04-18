# Tasks: penalty-system

## Status: planned
## TDD Mode: STRICT

## Batches

### Batch 1: Foundations — Models, Migrations, Exceptions
- [x] TASK-1: [RED] Add failing model tests for `Athlete.is_disqualified`, `Tournament.scheduling_gap_seconds`, `StandingsDeltaLog`, and exception imports in `tests/test_penalty_foundations.py`.
- [x] TASK-2: [GREEN] Add `Athlete.is_disqualified: bool` in `kakumi_app/models/athlete_model.py`; add `Tournament.scheduling_gap_seconds: int = Field(default=75)` in `kakumi_app/models/tournament_model.py`; add `StandingsDeltaLog` model in `kakumi_app/models/tournament_model.py`.
- [x] TASK-3: [GREEN] Create `kakumi_app/services/exceptions.py` with `PenaltyRemovalNotAllowedError`, `AthleteSchedulingConflictError`, `PenaltyEscalationError`.
- [x] TASK-4: [RED] Add failing schema tests for new table, columns, and indexes in `tests/test_penalty_migrations.py`.
- [x] TASK-5: [GREEN] Create `alembic/versions/*_add_penalty_system_fields.py` for `is_disqualified`, `scheduling_gap_seconds`, `standings_delta_logs` table, `ix_penalties_match_participant`, and `ix_matches_tatami_start_time` indexes. Include downgrade path.
- [x] TASK-6: [REFACTOR] Finalize defaults, metadata, and downgrade coverage across the foundation files.

### Batch 2: Core Service — apply_penalty and escalation
- [x] TASK-7: [RED] Add failing escalation and match-end tests in `tests/test_kumite_penalty_service.py`.
- [x] TASK-8: [GREEN] Update `kakumi_app/services/kumite_scoring_service.py` for escalation, `with_for_update()`, retries, and `PenaltyEscalationError`.
- [x] TASK-9: [REFACTOR] Extract typed lock/count helpers in `kakumi_app/services/kumite_scoring_service.py`.

### Batch 3: SHIKKAKU Round-Robin logic
- [x] TASK-10: [RED] Add failing last-bout, non-last, individual, and team RR tests in `tests/test_shikkaku_round_robin.py`.
- [x] TASK-11: [GREEN] Implement RR helpers and `_apply_shikkaku_round_robin()` in `kakumi_app/services/kumite_scoring_service.py`.
- [x] TASK-12: [REFACTOR] Normalize WKF notes, helper names, and shared branches in the same service.

### Batch 4: Scheduling overlap enforcement
- [x] TASK-13: [RED] Add failing tests for `check_athlete_scheduling_overlap()` — overlap detected, no overlap, no start_time skip, custom gap, default gap=75s — in `tests/test_scheduling_overlap.py`.
- [x] TASK-14: [GREEN] Create `kakumi_app/services/scheduling_service.py` with `check_athlete_scheduling_overlap(session, athlete_id, match_id, gap_seconds: int) -> None`; raises `AthleteSchedulingConflictError`. Wire call into `kumite_scoring_service.apply_penalty()` BEFORE the `with_for_update()` lock. Use Python-side `timedelta` arithmetic for SQLite compatibility.
- [x] TASK-15: [REFACTOR] Consolidate overlap window math and reusable queries in `kakumi_app/services/scheduling_service.py`.

### Batch 5: remove_last_penalty guard
- [x] TASK-16: [RED] Add failing guard and de-escalation tests in `tests/test_penalty_removal.py`.
- [x] TASK-17: [GREEN] Enforce `IN_PROGRESS`-only removal and safe recalculation in `kakumi_app/services/kumite_scoring_service.py`.
- [x] TASK-18: [REFACTOR] Extract guard/rebuild helpers in `kakumi_app/services/kumite_scoring_service.py`.

### Batch 6: StandingsDeltaLog — SHIKKAKU audit and revert
- [x] TASK-19: [RED] Add failing snapshot, JSON round-trip, and revert tests in `tests/test_revert_shikkaku.py`.
- [x] TASK-20: [GREEN] Implement snapshot persistence and `revert_shikkaku()` in `kakumi_app/services/kumite_scoring_service.py`.
- [x] TASK-21: [REFACTOR] Deduplicate snapshot serialization and restore mapping in the same service.

### Batch 7: KumiteMatchState (Reflex) — timer pause + sync
- [x] TASK-22: [RED] Add failing state tests for pause-before-submit, sync, and error feedback in `tests/test_kumite_match_state.py`.
- [x] TASK-23: [GREEN] Create `kakumi_app/states/kumite_match_state.py` with JSON-safe vars, async handlers, and backend sync.
- [x] TASK-24: [REFACTOR] Extract state-mapping helpers and shared operator messages in `kakumi_app/states/kumite_match_state.py`.

### Batch 8: Integration & Postgres CI tests
- [x] TASK-25: [RED] Add failing integration tests for spec scenarios 1–8 in `tests/test_penalty_system_integration.py` and PostgreSQL contention tests in `tests/test_penalty_concurrency.py`.
- [x] TASK-26: [GREEN] Extend `tests/conftest.py` and pytest config files with RR, team, tatami, and PostgreSQL-only fixtures/markers.
- [x] TASK-27: [REFACTOR] Remove duplicated fixture setup and finalize scenario naming across all penalty tests.

## Dependencies
- Batch 1 → Batches 2–8.
- Batch 2 → Batches 3, 5, 7, 8.
- Batch 3 → Batches 6, 8.
- Batch 4 → Batch 8.
- Batch 5 → Batches 7, 8.
- Batch 6 → Batch 8.
- Batch 7 → Batch 8.

## Notes
- Concurrency tests require PostgreSQL; skip or guard them in SQLite CI.
- All tests go in `tests/`; shared fixtures belong in `tests/conftest.py`.
- Preserve strict RED → GREEN → REFACTOR order inside each batch.
