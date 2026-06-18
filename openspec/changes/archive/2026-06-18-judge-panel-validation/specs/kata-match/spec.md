# Delta for Kata Match — Judge Loading

## ADDED Requirements

### Requirement: Judge Loading for Kata Matches — No Role Filter

When loading referees as judges for a kata match, the system MUST select ALL `Referee` rows without filtering by role. The query MUST be `select(Referee)` with no `where` clause restricting by referee role.

Kata modality does not distinguish referee roles (e.g., "judge" vs "referee" vs "arbitro"). All referees in the database are eligible to serve as judges on a kata panel.

#### Scenario: Load judges without role filter

- GIVEN a kata match is being loaded for display or judging setup
- WHEN the system queries referees to populate `_judge_ids_by_slot`
- THEN the query MUST be `select(Referee).order_by(Referee.id.asc())`
- AND the query MUST NOT include any `.where()` clause filtering by role
- AND ALL `Referee` rows in the database MUST be candidates for the panel

#### Scenario: Up to panel_size judges assigned

- GIVEN a kata match with `panel_size` of e.g. 5
- WHEN the query returns N referees
- THEN the first `min(panel_size, N)` referees (ordered by `id`) MUST be assigned to `_judge_ids_by_slot`
- AND the slot keys MUST follow the pattern `J1`, `J2`, ..., `J{panel_size}`
