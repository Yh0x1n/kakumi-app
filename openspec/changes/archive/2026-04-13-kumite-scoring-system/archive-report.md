# Archive Report: kumite-scoring-system

## Summary
Change `kumite-scoring-system` archivado exitosamente. SDD cycle completo.

## Archived to
`openspec/changes/archive/2026-04-13-kumite-scoring-system/`

## Artifacts
| File | Description |
|------|-------------|
| `explore.md` | Corrected WKF 2026 exploration (verified against official PDF) |
| `proposal.md` | Change proposal — scope, approach, risks |
| `spec.md` | Full specification with requirements and scenarios |
| `design.md` | Technical design — architecture decisions, service interface, dataclasses |
| `tasks.md` | Implementation task checklist (all 4 phases complete) |
| `verify-report.md` | Verify report — PASS, 233/233 tests, ruff clean |

## Files Changed in Codebase
| File | Action |
|------|--------|
| `kakumi_app/models/tournament_model.py` | Modified — added 8 fields to Match, applied_by_id to MatchScore |
| `alembic/versions/f0988d9c3f59_add_kumite_scoring_fields.py` | Created — SQLite-safe migration |
| `kakumi_app/services/kumite_scoring_service.py` | Created — KumiteScoringService (4 public methods, 25 tests) |
| `tests/test_kumite_scoring_service.py` | Created — 25 Strict TDD tests |

## Key Decisions
- YUKO=1, WAZA-ARI=2, IPPON=3 (verified Art. 8.6 WKF 2026)
- Match ends at lead >= 8 (NOT on single IPPON)
- Operator-applied scoring only (no judge input capture)
- SENSHU: manual flag, manual revocation via operator panel
- HANSOKU: differentiated by competition_system (elimination vs round-robin Art. 12.3.2)

## Tech Debt Remaining
- SQLAlchemy `overlaps=` on `Match.aka` / `Match.ao`
- JWT secret length in auth tests

## Date
2026-04-13
