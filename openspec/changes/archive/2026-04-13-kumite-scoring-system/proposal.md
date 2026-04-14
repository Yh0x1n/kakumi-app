# Proposal: Kumite Scoring System (WKF 2026)

## Intent
Implement a strictly WKF 2026-compliant Kumite scoring system for the kakumi-app tournament management platform.

## Scope
- Core scoring logic: YUKO=1, WAZA-ARI=2, IPPON=3
- 8-point lead match termination (NOT single IPPON)
- SENSHU flag tracking (first unopposed score, manual revocation by operator)
- Tiebreaker resolution: SENSHU → IPPON count → WAZA-ARI count → HANTEI/HIKIWAKE
- Penalty escalation: CHUI (max 3) → HANSOKU CHUI → HANSOKU
- HANSOKU differentiated behavior: elimination (direct win) vs round-robin (Art. 12.3.2: 4-0 or keep score if >4)
- Operator-applied scoring: no judge input capture, no majority validation

## Out of Scope
- UI components (future task)
- Timer/chronometer integration
- Bracket generation

## Approach
Hybrid Service + State architecture:
- `KumiteScoringService`: pure Python business logic, no Reflex dependency
- Reflex State: thin wrapper for UI reactivity (future task)
- SQLModel models: minimal additive extensions to existing Match and MatchScore

## Risk Level
Medium — match termination edge cases, SENSHU revocation, round-robin HANSOKU differentiation.

## Rollback Plan
Alembic downgrade migration removes new fields. Service file can be deleted without affecting existing models.
