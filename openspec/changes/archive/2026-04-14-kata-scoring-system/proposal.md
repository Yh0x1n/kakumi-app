# Kata Scoring System (WKF 2026) - Change Proposal

## Intent
Implement the comprehensive WKF 2026 compliant Kata scoring system to support individual and team competitions, including numerical judging (5.0–10.0 scale), FLAG manual contingencies, and complex Round-Robin tie-breaking mechanisms. This enables the application to seamlessly manage Kata tournaments alongside existing Kumite functionalities.

## Scope
**IN Scope:**
- Creation of new SQLModel entities: `KataJudgeScore` and `KataRoundStanding`.
- Addition of `aka_team_id` and `ao_team_id` to the existing `Match` model.
- Implementation of a stateless, pure Python `KataScoringService` following the pattern of `kumite_scoring_service.py`.
- Logic for calculating majority vote winners, assigning Victory Points (VP), and executing cascading tie-breakers (VP -> Head-to-head -> Vote sum -> Extra Kata).
- Logic for configurable Bunkai requirements per tournament (none, medals only, entire tournament).
- Strict TDD implementation with exhaustive pytest coverage for all tie-breaker scenarios.

**OUT of Scope:**
- UI/Frontend components for the Kata scoring panel (to be handled in a separate UI-focused change).
- World Ranking tie-breakers (permanently out of scope as this is for regional competitions).

## Approach
Adopt Approach A identified during exploration: introduce dedicated `KataJudgeScore` and `KataRoundStanding` models to strictly represent Kata's unique 5.0-10.0 scale and majority voting system without polluting Kumite models. Implement a pure Python `KataScoringService` to encapsulate all complex business logic, enabling comprehensive strict TDD without database or UI coupling, directly mirroring the proven `kumite_scoring_service.py` architecture.

## Key Decisions
1. **Dedicated Kata Models:** Create `KataJudgeScore` instead of overloading existing score models. This enforces the unique constraint of individual judge scores and majority voting logic natively.
2. **Unified Match Model:** Add nullable `aka_team_id` and `ao_team_id` to the existing `Match` model rather than creating a separate `TeamMatch` entity, simplifying tournament bracket logic and leveraging existing structures. We will also add a new field to track the bunkai requirement at the tournament level (none, medals only, entire tournament).
3. **Stateless Service Pattern:** Use a pure Python `KataScoringService` for all calculation logic (majority vote calculation, VP assignment, tie-breakers) to enable strict TDD (RED→GREEN→REFACTOR).

## Risks
1. **Complex Tie-breaking Logic (Risk of Bugs):** The cascading rules for Round-Robin (Art. 5.11/5.12) are complex.
   *Mitigation:* Exhaustive parameterized pytest fixtures covering all WKF 2026 tie-breaker edge cases, developed strictly via TDD.
2. **Database Migration Complexities:** Modifying the existing `Match` model to support teams could break existing queries.
   *Mitigation:* Provide robust Alembic upgrade/downgrade paths with nullable fields, ensuring backward compatibility with individual matches.

## Success Criteria
- `KataScoringService` passes 100% of TDD tests for numerical scoring, FLAG scoring, and all Round-Robin individual and team tie-breaker scenarios.
- New database models (`KataJudgeScore`, `KataRoundStanding`) and `Match` extensions successfully migrate via Alembic.
- No JavaScript/TypeScript is introduced (100% Python).
