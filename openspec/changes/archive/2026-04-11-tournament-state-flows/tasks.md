# Tasks: Flujos de estado de torneo

## Phase 1: Infrastructure

- [x] 1.1 Create `kakumi_app/models/tournament_event_logs.py` with `TournamentEventLog` model and index on `tournament_id`
- [x] 1.2 Add `is_transitioning: bool = False` field to `Tournament` model in `kakumi_app/models/tournament_model.py`
- [x] 1.3 Run migrations for the new model and field

## Phase 2: Core Implementation

- [x] 2.1 Implement `TournamentService` in `kakumi_app/services/tournament_service.py` with `VALID_TRANSITIONS` and `can_transition()`
- [x] 2.2 Add `validate_preconditions()` and `transition_to()` logic to `TournamentService`
- [x] 2.3 Implement `TournamentState` in `kakumi_app/states/tournament_state.py` with event handlers for each transition

## Phase 3: Integration

- [x] 3.1 Wire `TournamentState` event handlers to call `TournamentService.transition_to()`
- [x] 3.2 Add RBAC checks to `TournamentState` methods to ensure only authorized users can trigger transitions
- [x] 3.3 Ensure logs are created in `tournament_event_logs` during transitions

## Phase 4: Testing

- [x] 4.1 Unit tests for `TournamentService.can_transition()` covering all valid and invalid combinations
- [x] 4.2 Unit tests for `TournamentService.validate_preconditions()` for each state
- [x] 4.3 Integration tests for full state transitions and audit log persistence
