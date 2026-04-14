# Kata Scoring System Specification

## Purpose
Define the requirements and scenarios for the Kata scoring system, encompassing numerical and flag-based voting, round-robin standings with tie-breaking cascade (WKF 2026 rules), and Team Kata specifics.

## Requirements

### Requirement: Data Models
The system MUST provide data models to store Kata scores, round standings, and match team assignments.

#### Scenario: Store Numerical Score
- GIVEN a Match with 5 or 7 judges
- WHEN a judge submits a numerical score (5.0-10.0, 0.0 for DQ)
- THEN a `KataJudgeScore` record is created linking the judge, match, and performer.

#### Scenario: Match Team Assignment
- GIVEN a Team Kata Match
- WHEN the match is configured
- THEN `aka_team_id` and `ao_team_id` MUST be populated in the Match record.

### Requirement: KataScoringService — Numerical Mode
The system MUST calculate match winners and assign Victory Points based on numerical scores converted to votes.

#### Scenario: Calculate Numerical Winner
- GIVEN a match with 5 judges
- WHEN judges submit scores for AKA and AO
- THEN the system MUST compare each judge's AKA and AO scores to determine their vote, and the athlete with the majority of votes (3+) wins.
- AND the winner receives 3 VP and the loser 0 VP.

### Requirement: KataScoringService — FLAG Mode
The system MUST support a contingency flag mode where judges vote directly for AKA or AO.

#### Scenario: Calculate Flag Winner
- GIVEN a match operating in Flag Mode
- WHEN judges submit direct flag votes for AKA or AO
- THEN the system MUST aggregate the votes and the athlete with the majority (e.g., 3+ out of 5) wins.
- AND the winner receives 3 VP and the loser 0 VP.

### Requirement: Round-Robin Standings & Tie-breaking
The system MUST accumulate VP and resolve ties using the cascade: VP > Head-to-head > Sum of votes > Extra Kata.

#### Scenario: Tie-breaking by Head-to-head
- GIVEN two athletes tied on total VP in a round-robin pool
- WHEN their standing is calculated
- THEN the athlete who won the direct head-to-head match between them MUST be ranked higher.

#### Scenario: Tie-breaking by Extra Kata
- GIVEN two athletes tied on VP, Head-to-head, and total votes received
- WHEN their standing is calculated
- THEN the system MUST flag the standing for a manual "Extra Kata" resolution.

### Requirement: Team Kata Specifics & Bunkai Configuration
The system MUST support team matches with 3 out of 4 members and configurable Bunkai requirements at the tournament level (none, medals only, all rounds).

#### Scenario: Bunkai Configuration - None
- GIVEN a tournament configured with no Bunkai requirement
- WHEN any Team Kata match is generated
- THEN the `bunkai_required` flag MUST be set to false.

#### Scenario: Bunkai Configuration - Medals Only
- GIVEN a tournament configured with Bunkai required in medal rounds only
- WHEN a medal round Team Kata match is generated
- THEN the `bunkai_required` flag MUST be set to true.
- AND WHEN a non-medal round Team Kata match is generated
- THEN the `bunkai_required` flag MUST be set to false.

#### Scenario: Bunkai Configuration - All Rounds
- GIVEN a tournament configured with Bunkai required in all rounds
- WHEN any Team Kata match is generated
- THEN the `bunkai_required` flag MUST be set to true.

### Requirement: Validation & Error Handling
The system MUST reject invalid scores and configuration states.

#### Scenario: Reject Out-of-Range Score
- GIVEN a numerical score submission
- WHEN the score is 10.5 or 4.5
- THEN the system MUST raise a `KataScoreValidationError`.

#### Scenario: Reject Duplicate Score
- GIVEN a judge has already scored an athlete in a match
- WHEN the same judge submits another score for the same athlete
- THEN the system MUST raise a `KataDuplicateScoreError`.
