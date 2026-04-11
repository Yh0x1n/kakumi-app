# Design: Kakumi Tournament Manager Architecture

## Technical Approach

Transform the comprehensive WKF 2026 specification into a Reflex-based Python application following a clean architecture pattern. The system will use SQLModel for data persistence, Reflex State for reactive UI updates, and Python service layers for business logic. All tournament operations (scoring, penalties, brackets) will be implemented as pure Python modules with no JavaScript.

## Architecture Decisions

### Decision: Single-State vs Multi-State Pattern

**Choice**: Multi-State architecture with domain-specific State classes
**Alternatives considered**: Single global State class
**Rationale**: Reflex recommends small, focused State classes. We'll use separate State classes for TournamentState, MatchState, ScoringState, etc. to avoid monolithic state and improve testability.

### Decision: Direct SQLModel vs Repository Pattern

**Choice**: Direct SQLModel with service layer abstraction
**Alternatives considered**: Full repository pattern with interfaces
**Rationale**: Reflex's session context already provides transaction management. Adding a repository layer would duplicate data access logic. Service layer will handle business logic while models handle persistence.

### Decision: Synchronous vs Asynchronous Operations

**Choice**: Synchronous with background tasks for long operations
**Alternatives considered**: Full async with asyncio
**Reflex's model**: Reflex is synchronous by design. Long operations (bracket generation, CSV import) will use background tasks with progress indicators.

### Decision: State Management for Real-time Scoring

**Choice**: Polling with rx.interval for match updates
**Alternatives considered**: WebSockets or server-sent events
**Rationale**: Reflex's built-in reactive system handles real-time updates via state changes. `rx.interval` provides simple polling for timer updates without external dependencies.

### Decision: Component Architecture Pattern

**Choice**: Atomic design with Python functions
**Alternatives considered**: Class-based components
**Rationale**: Reflex components are functions. We'll organize them as: atoms (basic inputs), molecules (composed components), organisms (full sections), templates (page layouts).

## Data Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  UI Layer   │───▶│ State Layer │───▶│ Service Layer│
│ (Components)│    │ (rx.State)  │    │ (Business)   │
└─────────────┘    └─────────────┘    └─────────────┘
                           │                    │
                           ▼                    ▼
                    ┌─────────────┐    ┌─────────────┐
                    │   Models    │◀───│  Database   │
                    │ (SQLModel)  │    │  (SQLite)   │
                    └─────────────┘    └─────────────┘

Key Flows:
1. Scoring: Judge Input → MatchState → ScoringService → Update MatchScore → Refresh UI
2. Penalties: Referee Action → PenaltyService → Update Penalty → Update Match Status
3. Brackets: Category Start → BracketService → Generate Matches → Update Category
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `kakumi_app/models/` | Modify | Expand models to match spec (add all models from Section 2) |
| `kakumi_app/services/` | Create | Business logic services (scoring, penalties, brackets, import/export) |
| `kakumi_app/states/` | Create | Domain-specific State classes (TournamentState, MatchState, etc.) |
| `kakumi_app/components/` | Expand | Add all UI components per spec Section 11 |
| `kakumi_app/pages/` | Expand | Implement all routes from spec Section 11.1 |
| `kakumi_app/utils/` | Create | Helper functions (date validation, weight checking, etc.) |
| `kakumi_app/auth/` | Create | Authentication and authorization logic |
| `kakumi_app/styles/` | Expand | Style constants for consistent theming |

## Interfaces / Contracts

### State Interfaces

```python
class TournamentState(rx.State):
    tournaments: List[Tournament]
    current_tournament: Optional[Tournament]
    tournament_status: str  # PLANIFICADO -> INSCRIPCION -> etc.
    
    def create_tournament(self, data: dict) -> Tournament
    def update_status(self, new_status: str) -> None
    def validate_transition(self, from_status: str, to_status: str) -> bool

class MatchState(rx.State):
    current_match: Optional[Match]
    aka_score: int = 0
    ao_score: int = 0
    penalties: List[Penalty]
    timer_seconds: int = 180
    is_running: bool = False
    
    def add_score(self, participant: str, score_type: str) -> None
    def add_penalty(self, penalty: Penalty) -> None
    def start_timer(self) -> None
    def stop_timer(self) -> None
```

### Service Interfaces

```python
class ScoringService:
    @staticmethod
    def calculate_match_score(match_id: int) -> dict:
        """Returns {aka_score, ao_score, winner_id}"""
    
    @staticmethod
    def validate_technique(technique_data: dict) -> bool:
        """Validates WKF 2026 scoring criteria"""

class PenaltyService:
    @staticmethod
    def apply_penalty(match_id: int, participant: str, penalty_type: str) -> Penalty:
        """Applies penalty and updates accumulation"""
    
    @staticmethod
    def check_disqualification(match_id: int, participant: str) -> bool:
        """Checks if participant should be disqualified"""

class BracketService:
    @staticmethod
    def generate_bracket(category_id: int) -> List[Match]:
        """Generates bracket based on seeding rules"""
    
    @staticmethod
    def advance_winner(match_id: int) -> None:
        """Advances winner to next round"""
```

### Model Contracts (Key Relationships)

```python
# Match to Penalty (1:N)
class Match(rx.Model, table=True):
    penalties: List["Penalty"] = Relationship(back_populates="match")

# Penalty accumulation logic
class Penalty(rx.Model, table=True):
    match_id: int = Field(foreign_key="match.id")
    penalty_type: str  # CHUI, HANSOKU_CHUI, HANSOKU, SHIKKAKU
    is_accumulated: bool  # True if part of accumulation sequence
    
    # Business rule: penalty_type determines next penalty in sequence
    # CHUI → CHUI → CHUI → HANSOKU_CHUI → HANSOKU
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Service logic (scoring, penalties, brackets) | pytest with mock models |
| Unit | State transitions and validations | Test State classes directly |
| Integration | Database operations with transactions | Use reflex session context |
| Integration | CSV/JSON import/export | Test with sample files |
| E2E | Complete match flow from start to finish | Manual testing initially, later automated |

## Migration / Rollout

**Phase 1: Core Models & Database**
- Implement all models from spec Section 2
- Run Alembic migrations
- Basic CRUD operations

**Phase 2: Tournament Workflow**
- Implement tournament status transitions
- Add category management
- Basic bracket generation

**Phase 3: Scoring Systems**
- Kumite scoring (Ippon/Waza-ari/Yuko)
- Kata scoring (judges panel, averages)
- Penalty system with WKF 2026 rules

**Phase 4: Real-time Features**
- Match timer
- Live scoring display
- Bracket visualization

**Phase 5: Import/Export & Polish**
- CSV/JSON import for athletes
- Result export
- UI polish and responsive design

**Phase 6: Authentication & Authorization**
- User roles (ADMIN/OPERATOR/VIEWER)
- Session management
- Permission matrix

## Open Questions

- [ ] How to handle real-time updates for multiple tatamis simultaneously?
- [ ] Should we implement optimistic locking for concurrent score updates?
- [ ] What's the maximum number of judges (5 vs 7) for international events?
- [ ] Should bracket seeding use external ranking data or internal tournament results?