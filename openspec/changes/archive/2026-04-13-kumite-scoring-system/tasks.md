# Tasks: Kumite Scoring System

## Phase 1: Schema + RED Tests

- [x] 1.1 Update `kakumi_app/models/tournament_model.py` to add `Match` SENSHU/count fields and `MatchScore.applied_by_id`, preserving existing enums, relationships, and defaults.
- [x] 1.2 Create one SQLite-safe Alembic revision in `alembic/versions/` adding server defaults for new non-null `matches` columns and nullable `match_scores.applied_by_id`, with full downgrade.
- [x] 1.3 Create `tests/test_kumite_scoring_service.py` fixtures/helpers for an `IN_PROGRESS` match, operator user, and score setup, following existing pytest patterns.
- [x] 1.4 RED: write failing tests for YUKO/WAZA_ARI/IPPON values, `MatchScore` audit creation, score-type counters, and "IPPON alone does not end / lead >= 8 ends" using `source .venv/bin/activate && python -m pytest tests/ -v`.

## Phase 2: Score Service GREEN

- [x] 2.1 Create `kakumi_app/services/kumite_scoring_service.py` with typed result dataclasses, service constants, and static-method structure matching `kakumi_app/services/tournament_service.py`.
- [x] 2.2 Implement `apply_score`, `_set_senshu_if_first`, and `_check_match_termination` to validate `IN_PROGRESS`, update totals and per-type counts, persist `applied_by_id`, award SENSHU only on first unopposed score, and terminate only on >= 8 lead.
- [x] 2.3 GREEN: make Phase 1 scoring tests pass and harden invalid-state / invalid-score error paths with docstrings, type hints, and transaction-safe session handling.

## Phase 3: Penalties + Tiebreakers

- [x] 3.1 RED: add failing tests for CHUI escalation, HANSOKU_CHUI -> HANSOKU, HANSOKU termination with opponent YUKO record, SENSHU revocation, and tiebreak priority `SENSHU > IPPON > WAZA_ARI > HANTEI/HIKIWAKE`.
- [x] 3.2 Implement `_get_next_penalty_level`, `apply_penalty`, `revoke_senshu`, and `_get_tiebreaker_winner` with WKF 2026 rules, including opponent win handling on HANSOKU and manual SENSHU removal.
- [x] 3.3 GREEN: make penalty/tiebreak tests pass, including negative cases for completed matches and invalid inputs.

## Phase 4: Refactor + Verification

- [x] 4.1 REFACTOR: remove duplication in score/count updates, keep Ruff complexity <= 10, and align imports, naming, and docstrings with project conventions.
- [x] 4.2 Run the full test target `source .venv/bin/activate && python -m pytest tests/ -v` → 233 passed.
- [x] 4.3 Verify the final implementation against `spec.md` and `design.md`: operator-only flow, no UI work, SQLite-safe defaults, required service API, and exact WKF 2026 rule ordering.
