# Specification: Kumite Scoring System (WKF 2026)

## Purpose
Define the data models, scoring rules, penalty escalation, UI components, and test cases for the Kakumi App Kumite Scoring System, strictly following WKF 2026 rules.

## 1. Data Models (SQLModel)

### Requirement: Match and Score Entities
The system MUST use SQLModel to persist match state.

#### Scenario: Track Scores and Penalties
- GIVEN a `Match` record
- WHEN scores or penalties are registered
- THEN the system MUST track `aka_score`, `ao_score`, `aka_senshu`, `ao_senshu`, and counts for IPPON/WAZA_ARI/YUKO.
- AND `ScoreType` MUST be an Enum: `IPPON` (3), `WAZA_ARI` (2), `YUKO` (1), `PENALTY`, `WARNING`.
- AND individual score events MUST be stored as `MatchScore` records with the operator who applied them.

## 2. Business Logic: Operator-Applied Scoring

### Requirement: Manual Score Application
Scores MUST be applied manually by the operator when the head referee confirms the point.

#### Scenario: Operator applies confirmed score
- GIVEN a technique is confirmed by the head referee
- WHEN the operator selects YUKO (1pt), WAZA_ARI (2pts), or IPPON (3pts) and applies it to an athlete
- THEN the system MUST award the points to the selected athlete without further validation.
- AND individual judge inputs are not captured separately — only the confirmed score from the head referee matters.

## 3. Match Termination Rules

### Requirement: 8-Point Lead Superiority
The match MUST end immediately if one athlete achieves a lead of 8 points.

#### Scenario: Superiority Win
- GIVEN a match in progress
- WHEN AKA scores and the point differential (`|aka_score - ao_score|`) becomes >= 8
- THEN the system MUST immediately terminate the match and declare AKA the winner.
- AND single IPPON scores MUST NOT terminate the match unless an 8-point lead is achieved.

## 4. Tiebreakers at Time Expiry

### Requirement: Tie-breaking Resolution
When time expires, the system MUST determine the winner based on priority.

#### Scenario: Equal points at time up
- GIVEN time has expired and `aka_score == ao_score`
- WHEN determining the winner
- THEN the system MUST award the win to the athlete with SENSHU (first unopposed score).
- AND if no SENSHU, to the athlete with more IPPON.
- AND if equal IPPON, to the athlete with more WAZA-ARI.
- AND if still equal, the match MUST require HANTEI (judge vote) or HIKIWAKE (draw).

## 5. Penalty Escalation Rules

### Requirement: 4-Step Penalty Escalation
Penalties MUST follow a 4-step escalation.

#### Scenario: Applying consecutive penalties
- GIVEN an athlete commits minor infractions
- WHEN applying penalties
- THEN the system MUST assign CHUI up to 3 times.
- AND the 4th infraction MUST escalate to HANSOKU CHUI.
- AND the next infraction MUST escalate to HANSOKU (Disqualification).
- AND points awarded to the opponent from a HANSOKU MUST be recorded as YUKO.

## 6. Service Requirements

### Requirement: Kumite Scoring Service
The system MUST provide a backend service for applying scores manually by operator.

#### Scenario: Operator applies score to match
- GIVEN a match in progress
- WHEN the operator applies a YUKO/WAZA_ARI/IPPON to an athlete
- THEN the system MUST validate that the match is in IN_PROGRESS state
- AND apply the score to the athlete's total
- AND create a MatchScore record with the operator who applied it
- AND check for 8-point lead termination condition after applying score.

## 7. Test Cases (Strict TDD)

### Requirement: Unit Test Coverage
The `KumiteScoringService` MUST have pytest test cases verifying the rules.

#### Scenario: Core Rules Tests
- GIVEN the scoring service
- WHEN tests are executed
- THEN tests MUST verify that YUKO=1, WAZA_ARI=2, IPPON=3.
- AND verify that IPPON alone does NOT end the match.
- AND verify that an 8-point lead ends the match.
- AND verify SENSHU, IPPON, and WAZA_ARI tiebreaker logic.
- AND verify that operator can apply scores manually to athletes.
- AND verify that MatchScore records are created when operator applies scores.
