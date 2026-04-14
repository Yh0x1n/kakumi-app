# Design: Kumite Scoring System (WKF 2026)

## Architecture Overview
Pure-Python `KumiteScoringService` (static methods, no Reflex dependency) with minimal additive model extensions and a single Alembic migration.

## Architecture Decisions

### AD-1: Static service methods (no instance state)
Same pattern as `tournament_service.py`. Stateless — all data read/written via `rx.session()`. No DI container needed.

### AD-2: Derive tiebreaker counts from persisted fields
Cache per-type counts (aka_ippon_count, etc.) on Match directly. Avoids aggregate queries at tiebreak time. Tradeoff: must keep counts consistent on every apply_score call.

### AD-3: Operator-only scoring (no judge input capture)
No majority validation, no per-judge MatchScore rows for each signal. Operator sees physical signals, head referee concedes, operator presses button. One MatchScore per awarded point, with applied_by_id (operator user FK).

### AD-4: SENSHU is manual flag, not computed
aka_senshu / ao_senshu stored as booleans on Match. Set automatically on first unopposed score. Revoked manually by operator via revoke_senshu(). No timer coupling.

### AD-5: HANSOKU behavior differs by competition_system
- ELIMINATION: direct win for opponent, no special scoring
- ROUND_ROBIN (Art. 12.3.2): opponent gets max(4, current_opponent_score), all as YUKO. Disqualified athlete score → 0.

### AD-6: Single combined Alembic migration (SQLite-safe)
One revision file adds all new fields. server_default used for all non-nullable additions. batch_alter_table for FK additions (SQLite limitation).

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `kakumi_app/models/tournament_model.py` | Modify | Add 8 fields to Match + applied_by_id to MatchScore |
| `alembic/versions/<hash>_add_kumite_scoring_fields.py` | Create | SQLite-safe migration |
| `kakumi_app/services/kumite_scoring_service.py` | Create | Full scoring service |
| `tests/test_kumite_scoring_service.py` | Create | 25 Strict TDD tests |

## Model Extensions

### Match (additive only)
```python
aka_senshu: bool = Field(default=False)
ao_senshu: bool = Field(default=False)
aka_ippon_count: int = Field(default=0)
ao_ippon_count: int = Field(default=0)
aka_waza_ari_count: int = Field(default=0)
ao_waza_ari_count: int = Field(default=0)
aka_yuko_count: int = Field(default=0)
ao_yuko_count: int = Field(default=0)
```

### MatchScore (additive only)
```python
applied_by_id: Optional[int] = Field(default=None, foreign_key="users.id")
```

## Service Interface

```python
class KumiteScoringService:
    # Public API
    @staticmethod
    def apply_score(match_id, participant, score_type, applied_by_id) -> MatchResult: ...
    @staticmethod
    def apply_penalty(match_id, participant, penalty_type, reason, applied_by_id) -> PenaltyResult: ...
    @staticmethod
    def revoke_senshu(match_id, participant) -> SenshuResult: ...
    @staticmethod
    def resolve_tiebreaker(match_id) -> TiebreakerResult: ...

    # Private helpers
    @staticmethod
    def _check_match_termination(match) -> Optional[str]: ...
    @staticmethod
    def _get_tiebreaker_winner(match) -> TiebreakerResult: ...
    @staticmethod
    def _set_senshu_if_first(match, participant) -> None: ...
    @staticmethod
    def _get_next_penalty_level(chui_count) -> PenaltyType: ...
    @staticmethod
    def _apply_hansoku_result(match, winner_participant, session) -> None: ...
```

## Return Dataclasses

```python
@dataclass
class MatchResult:
    success: bool
    match_ended: bool
    winner: Optional[str]
    message: str

@dataclass
class PenaltyResult:
    success: bool
    penalty_type: str
    match_ended: bool
    winner: Optional[str]
    message: str

@dataclass
class TiebreakerResult:
    winner: Optional[str]
    reason: str
    is_draw: bool

@dataclass
class SenshuResult:
    success: bool
    message: str
```

## Open Questions
- [x] SENSHU revocation: RESOLVED — manual operator action, no timer needed. Operator applies penalty then presses revoke button. `revoke_senshu(match_id, participant)` exposed as public method.
- [ ] Round-robin HANSOKU scoring (Art. 12.3.2): IMPLEMENTED — `_apply_hansoku_result` differentiates by competition_system.

## Test Architecture (Strict TDD)
- Fixtures: test match IN_PROGRESS, AKA/AO athletes, operator user (in conftest.py pattern)
- Groups: scoring (YUKO/WAZA_ARI/IPPON), termination (8-pt lead), SENSHU, tiebreakers, penalty escalation, HANSOKU round-robin
- 25 tests total, all passing
