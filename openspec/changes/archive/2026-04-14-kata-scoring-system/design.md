# Design: Kata Scoring System (WKF 2026)

## Technical Approach

Introduce a dedicated `KataScoringService` as a stateless, static-method service mirroring the proven `KumiteScoringService` architecture. New models `KataJudgeScore` and `KataRoundStanding` live in a separate `kata_model.py` to avoid polluting existing tournament models, while the existing `Match` model gains nullable team FK fields and a `bunkai_required` flag. Enums and scoring modes are defined alongside the new models. The `TournamentCategory` model gains a `bunkai_mode` field to store the tournament-level Bunkai configuration.

## Architecture Decisions

| Decision | Choice | Alternatives Rejected | Rationale |
|---|---|---|---|
| Judge FK target | `referees.id` (existing pattern) | `users.id` | Existing `MatchScore.judge_id` → `referees.id`. Judges are `Referee` with role=JUDGE. Stay consistent. |
| Score model location | New `kata_model.py` | Extend `tournament_model.py` | `tournament_model.py` is 465 lines. Separation keeps files focused; cross-model FKs via string refs. |
| Bunkai config storage | `bunkai_mode` field on `TournamentCategory` | Separate config table or on `Tournament` | Bunkai varies per category (one tournament may have team kata + individual kata). Category-level is the right granularity. |
| Service pattern | Static methods + `@dataclass` results | Instance-based / rx.State methods | Matches `KumiteScoringService` exactly: stateless, testable, `rx.session()` scoped. |
| Score validation | Custom exceptions (`raise`) | Return `MatchResult(success=False)` | Kumite uses result-objects for flow control; Kata needs hard failures for invalid data (score=15.0 is a bug, not user choice). Exceptions for validation, result-objects for flow. |
| BunkaiMode enum | String enum in `kata_model.py` | Store as plain string | Typed safety + reuse in service logic. Stored as `.value` per existing convention. |

## Data Flow

```
Operator UI ──→ KataScoringService (static methods)
                    │
                    ├─→ rx.session() ──→ KataJudgeScore (write per judge)
                    │
                    ├─→ calculate_match_winner() ──→ compare per-judge votes
                    │                                  ──→ MatchResult (AKA/AO/DRAW)
                    │
                    ├─→ assign_victory_points() ──→ KataRoundStanding (upsert)
                    │
                    └─→ calculate_standings() ──→ sorted list[KataRoundStanding]
                         │
                         └─→ resolve_tiebreaker() ──→ H2H / votes / flag extra kata
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `kakumi_app/models/kata_model.py` | Create | `KataJudgeScore`, `KataRoundStanding`, `FlagVote`, `BunkaiMode`, `KataScoringMode` enums, custom exceptions |
| `kakumi_app/services/kata_scoring_service.py` | Create | `KataScoringService` with all public methods + `KataMatchResult` dataclass |
| `tests/test_kata_scoring_service.py` | Create | Full TDD test suite |
| `kakumi_app/models/tournament_model.py` | Modify | Add `KATA_SCORE` to `ScoreType`; add `aka_team_id`, `ao_team_id`, `bunkai_required` to `Match`; add `bunkai_mode` to `TournamentCategory` |
| `tests/conftest.py` | Modify | Add kata-specific fixtures: `sample_judges`, `kata_match`, `kata_category`, `sample_team_2` |
| `alembic/versions/xxxx_add_kata_scoring.py` | Create | Migration for new tables + altered columns |

## Interfaces / Contracts

### New Enums & Dataclasses (`kata_model.py`)

```python
class FlagVote(str, Enum):
    AKA = "AKA"
    AO = "AO"

class BunkaiMode(str, Enum):
    NONE = "NONE"
    MEDALS_ONLY = "MEDALS_ONLY"
    ALL_ROUNDS = "ALL_ROUNDS"

class KataScoringMode(str, Enum):
    NUMERICAL = "NUMERICAL"
    FLAG = "FLAG"
```

### Custom Exceptions (`kata_model.py`)

```python
class KataScoreValidationError(Exception):
    """Score out of range (must be 0.0 or 5.0-10.0)."""

class KataDuplicateScoreError(Exception):
    """Judge already scored this performer in this match."""

class KataJudgeCountError(Exception):
    """Wrong number of judges for score calculation."""
```

### KataJudgeScore Model

```python
class KataJudgeScore(rx.Model, table=True):
    __tablename__ = "kata_judge_scores"
    judge_id: int = Field(foreign_key="referees.id", index=True)
    match_id: int = Field(foreign_key="matches.id", index=True)
    performer_id: Optional[int] = Field(default=None, foreign_key="athletes.id")
    team_id: Optional[int] = Field(default=None, foreign_key="teams.id")
    score: float = Field(default=0.0)  # 0.0 (DQ) or 5.0-10.0
    flag_vote: Optional[str] = Field(default=None)  # FlagVote.value
    is_flag_mode: bool = Field(default=False)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
```

### KataRoundStanding Model

```python
class KataRoundStanding(rx.Model, table=True):
    __tablename__ = "kata_round_standings"
    match_id: int = Field(foreign_key="matches.id", index=True)
    athlete_id: Optional[int] = Field(default=None, foreign_key="athletes.id")
    team_id: Optional[int] = Field(default=None, foreign_key="teams.id")
    victory_points: int = Field(default=0)
    votes_received: int = Field(default=0)
    needs_extra_kata: bool = Field(default=False)
```

### Match Extensions (added to existing `Match`)

```python
# New fields on Match
aka_team_id: Optional[int] = Field(default=None, foreign_key="teams.id")
ao_team_id: Optional[int] = Field(default=None, foreign_key="teams.id")
bunkai_required: bool = Field(default=False)
```

### TournamentCategory Extension

```python
# New field on TournamentCategory
bunkai_mode: str = Field(default=BunkaiMode.NONE.value)
```

### KataScoringService Public API

```python
@dataclass
class KataMatchResult:
    winner: Optional[str]       # "AKA" | "AO" | None
    aka_votes: int
    ao_votes: int
    is_draw: bool
    message: str

class KataScoringService:
    VALID_PANEL_SIZES: tuple[int, ...] = (5, 7)
    SCORE_MIN: float = 5.0
    SCORE_MAX: float = 10.0
    SCORE_DQ: float = 0.0
    VP_WIN: int = 3
    VP_LOSS: int = 0

    @staticmethod
    def record_numerical_score(
        match_id: int, judge_id: int, participant: str,
        performer_id: Optional[int], team_id: Optional[int],
        score: float,
    ) -> KataJudgeScore:
        """Record a 5.0-10.0 numerical score. Raises KataScoreValidationError / KataDuplicateScoreError."""

    @staticmethod
    def record_flag_vote(
        match_id: int, judge_id: int,
        flag_vote: FlagVote,
    ) -> KataJudgeScore:
        """Record a direct AKA/AO flag vote. Raises KataDuplicateScoreError."""

    @staticmethod
    def calculate_match_winner(match_id: int) -> KataMatchResult:
        """Compare per-judge votes (numerical: higher score wins that judge's vote). Majority → winner. Raises KataJudgeCountError if incomplete."""

    @staticmethod
    def assign_victory_points(
        match_id: int, winner_participant: str,
    ) -> tuple[KataRoundStanding, KataRoundStanding]:
        """Create/upsert standings: winner gets VP_WIN, loser gets VP_LOSS. Both get votes_received updated."""

    @staticmethod
    def calculate_standings(category_id: int) -> list[KataRoundStanding]:
        """Return standings sorted by cascade: VP desc → head-to-head → votes_received desc."""

    @staticmethod
    def resolve_tiebreaker(
        category_id: int,
        athlete_a_id: Optional[int], athlete_b_id: Optional[int],
        team_a_id: Optional[int], team_b_id: Optional[int],
    ) -> list[KataRoundStanding]:
        """Apply H2H → votes → flag needs_extra_kata. Returns updated standings."""
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Score validation (range, DQ, duplicates) | Parametrize: 0.0, 5.0, 7.5, 10.0, 4.9, 10.1, -1.0 |
| Unit | Majority vote: 3-2, 5-0, 4-3 (7 judges) | Parametrize panel sizes + vote distributions |
| Unit | VP assignment: winner=3, loser=0 | Direct assertion after `assign_victory_points` |
| Unit | Standings cascade: VP → H2H → votes → extra kata | Parametrize 4-athlete pools with various tie configs |
| Unit | Flag mode: vote recording + majority | Same majority logic, different input path |
| Unit | Bunkai mode: propagation from category to match | Test NONE/MEDALS_ONLY/ALL_ROUNDS × round type |
| Unit | Custom exceptions raised for invalid inputs | `pytest.raises` for each exception class |
| Integration | Full round-robin pool: record → calculate → standings | End-to-end flow through service layer with DB |

### Test File Structure (`tests/test_kata_scoring_service.py`)

- **Group: Score Recording** — numerical range, DQ, duplicate rejection
- **Group: Flag Voting** — vote recording, duplicate rejection
- **Group: Match Winner Calculation** — majority vote, draw, panel sizes 5 & 7
- **Group: Victory Points** — winner/loser VP, votes_received tracking
- **Group: Standings & Tie-breaking** — VP sort, H2H, votes sum, extra kata flag
- **Group: Bunkai Configuration** — mode propagation per category setting
- **Group: Validation Errors** — all 3 custom exception scenarios

### New Conftest Fixtures

- `sample_judges(n=5)` — creates n `Referee` with role=JUDGE
- `kata_category` — `TournamentCategory` with modality=KATA_INDIVIDUAL
- `kata_team_category` — with modality=KATA_TEAM + bunkai_mode
- `kata_match` — `Match` linked to kata_category
- `sample_team_2` — second team for team kata tests

## Migration Design

**New tables:**
- `kata_judge_scores` — 8 columns (id auto + 7 fields)
- `kata_round_standings` — 7 columns (id auto + 6 fields)

**Altered tables:**
- `matches` — ADD `aka_team_id` (nullable FK→teams), `ao_team_id` (nullable FK→teams), `bunkai_required` (bool default false)
- `tournament_categories` — ADD `bunkai_mode` (str default "NONE")

**Enum additions:**
- `ScoreType` — add `KATA_SCORE = "KATA_SCORE"` value (Python enum only, no DB enum migration needed — stored as string)

All new columns are nullable or have defaults → zero-downtime migration, backward compatible.
