# Design: Penalty System (Kumite)

> **STRICT TDD MODE IS ACTIVE** — Todo método nuevo DEBE tener tests escritos ANTES de la implementación. Red → Green → Refactor.

## Technical Approach

Extender infraestructura existente (`Penalty` model, `KumiteScoringService.apply_penalty()`) con: (1) campo `is_disqualified` en `Athlete`, (2) `match_time_seconds` en `Penalty` (ya existe), (3) lógica SHIKKAKU tournament-wide con bifurcación round-robin (último vs no-último encuentro) e individual vs equipos, (4) `remove_last_penalty()` con guard clause estricta, (5) DB-level locking con `with_for_update()` + backoff/retries, (6) `KumiteMatchState` en Reflex con timer sync, (7) scheduling constraint para impedir asignación de atleta a dos tatamis con overlap temporal, (8) rollback/compensation plan para cambios masivos en standings. NO se crea tabla nueva — `Penalty` ya existe.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|-------------|-----------|
| Tabla de penalties | Reusar `Penalty` existente | Crear `MatchPenalty` nueva | Ya tiene campos, FK, relaciones. Evita migración destructiva |
| DQ flag | `is_disqualified: bool` en `Athlete` | Tabla `Disqualification` | Spec lo pide así. Simple, queryable. SHIKKAKU es raro |
| Concurrencia | `with_for_update()` + backoff exponencial (3 retries) | Optimistic locking con version column | SQLite dev usa serialized txn (no-op); PG prod necesita row lock real |
| Timer sync | Frontend pausa local → backend confirma `match_time_seconds` | WebSocket bidireccional | Reflex no tiene WS custom. Round-trip state var, spec RF-04 |
| State pattern | Nuevo `KumiteMatchState(rx.State)` dedicado | Meter en `TournamentState` | Separación de concerns. Timer + penalties + scoring es complejo |
| Exceptions | Custom hierarchy: `PenaltyError` base | Generic ValueError | Validaciones WKF en service layer, tipos distintos para UI feedback |
| SHIKKAKU RR: último vs no-último | Bifurcación explícita por posición del encuentro en RR | Tratamiento uniforme | WKF Art. 10.7.2: último preserva; no-último ANULA |
| SHIKKAKU: individual vs equipos | Bifurcación por `category.modality` | Lógica unificada | WKF 3.7.3: resultado varía según modalidad |
| remove_last_penalty guard | `PenaltyRemovalNotAllowedError` si match no IN_PROGRESS | Silently ignore | Previene corrupción en matches cerrados |
| Scheduling constraint | `check_athlete_scheduling_overlap()` in NEW `scheduling_service.py`, called from `apply_penalty()` BEFORE penalty write | Constraint at DB level / app-level in `assign_match_to_tatami()` | Service-layer guard catches conflicts at penalty time; `match.tatami_id` not yet assigned in code so this is the first entry point. PINNED. |
| Rollback standings | Delta snapshot pre-aplicación + endpoint admin revert | Sin rollback | SHIKKAKU masivo afecta standings; admin necesita poder revertir errores |

## Data Flow

```
UI (KumiteMatchState)          Service Layer                    DB
─────────────────────          ─────────────────                ──
1. User clicks penalty
2. timer_running=False ←─ local pause (RF-04)
3. apply_penalty() ──────→ check_athlete_scheduling_overlap() ← PINNED
                           ├─ CONFLICT → raise, abort
                           └─ OK → acquire lock (FOR UPDATE + retry)
                           validate match IN_PROGRESS
                           count existing penalties
                           escalate if needed
                           check HANSOKU → end match
                           check SHIKKAKU → DQ athlete
                             ├─ RR? → _apply_shikkaku_round_robin()
                             │    ├─ is_last_match? → preserve prev scores
                             │    └─ NOT last? → nullify prev scores
                             │    ├─ INDIVIDUAL? → result per WKF individual
                             │    └─ TEAM? → result per WKF team
                             │    └─ SAVE DELTA SNAPSHOT (pre → post)
                             └─ ELIM? → DQ + opponent wins
                           cancel future advancement
                           record match_time_seconds
                           commit ────────────────────→ INSERT/UPDATE
                     ←──── PenaltyResult
4. sync timer from result
5. re-render UI

remove_last_penalty() ──→ guard: match.status == IN_PROGRESS
                           ├─ NO → raise PenaltyRemovalNotAllowedError
                           └─ YES → remove last, de-escalate, commit

assign_match_to_tatami() → check_athlete_overlap(athlete_id, tatami, time_range)
                           ├─ OVERLAP → raise SchedulingConflictError
                           └─ OK → assign + commit
```

## SHIKKAKU Round-Robin: Technical Approach

### `_apply_shikkaku_round_robin(match, penalized_participant, session)`

```python
def _apply_shikkaku_round_robin(match, penalized_participant, session):
    athlete_id = match.aka_id if penalized_participant == "AKA" else match.ao_id
    category = match.category
    is_team = category.modality == Modality.KUMITE_TEAM.value

    # 1. Snapshot delta ANTES de modificar (rollback/compensation)
    delta = _capture_standings_delta(athlete_id, category.id, session)

    # 2. ¿Último encuentro?
    is_last = _is_last_rr_match(match, athlete_id, session)

    # 3. Scores anteriores
    if not is_last:
        _nullify_rr_previous_scores(athlete_id, category.id, match.id, session)
    # Si es último: scores anteriores se MANTIENEN (no-op)

    # 4. DQ flag
    athlete = session.get(Athlete, athlete_id)
    athlete.is_disqualified = True

    # 5. Resultado match actual (bifurca individual/equipos)
    if is_team:
        _resolve_shikkaku_match_team(match, penalized_participant, session)
    else:
        _resolve_shikkaku_match_individual(match, penalized_participant, session)

    # 6. Cancelar matches restantes
    _cancel_remaining_rr_matches(athlete_id, category.id, match.id, session)

    # 7. Persistir delta para posible rollback admin
    _persist_standings_delta(delta, athlete_id, category.id, session)
```

### `_is_last_rr_match(match, athlete_id, session) -> bool`

```python
def _is_last_rr_match(match, athlete_id, session):
    """Consulta matches PENDING/READY/IN_PROGRESS del mismo category_id
    donde participe athlete_id (como aka_id o ao_id),
    EXCLUYENDO el match actual. Si count == 0 → es el último."""
    remaining = session.exec(
        select(func.count(Match.id)).where(
            Match.category_id == match.category_id,
            Match.id != match.id,
            Match.match_type == MatchType.ROUND_ROBIN.value,
            Match.status.in_([
                MatchStatus.PENDING.value,
                MatchStatus.READY.value,
                MatchStatus.IN_PROGRESS.value,
            ]),
            or_(Match.aka_id == athlete_id, Match.ao_id == athlete_id),
        )
    ).one()
    return remaining == 0
```

### `_nullify_rr_previous_scores(athlete_id, category_id, current_match_id, session)`

```python
def _nullify_rr_previous_scores(athlete_id, category_id, current_match_id, session):
    """Art. 10.7.2: Anula scores de matches COMPLETED anteriores
    del atleta en el mismo RR group. Pone scores a 0-0 y marca
    status CANCELLED (o campo nullified=True si se prefiere)."""
    prev_matches = session.exec(
        select(Match).where(
            Match.category_id == category_id,
            Match.id != current_match_id,
            Match.match_type == MatchType.ROUND_ROBIN.value,
            Match.status == MatchStatus.COMPLETED.value,
            or_(Match.aka_id == athlete_id, Match.ao_id == athlete_id),
        )
    ).all()

    for m in prev_matches:
        # Guardar scores originales en delta antes de nullificar
        m.aka_score = 0
        m.ao_score = 0
        m.winner_id = None  # El oponente gana por defecto (recalcular standings)
        m.notes = f"NULLIFIED: SHIKKAKU athlete {athlete_id}"
        session.add(m)
```

### `_cancel_remaining_rr_matches(athlete_id, category_id, current_match_id, session)`

```python
def _cancel_remaining_rr_matches(athlete_id, category_id, current_match_id, session):
    """Cancela matches futuros (PENDING/READY) del atleta DQ'd en el RR."""
    remaining = session.exec(
        select(Match).where(
            Match.category_id == category_id,
            Match.id != current_match_id,
            Match.match_type == MatchType.ROUND_ROBIN.value,
            Match.status.in_([
                MatchStatus.PENDING.value,
                MatchStatus.READY.value,
            ]),
            or_(Match.aka_id == athlete_id, Match.ao_id == athlete_id),
        )
    ).all()

    for m in remaining:
        m.status = MatchStatus.CANCELLED.value
        m.notes = f"CANCELLED: opponent SHIKKAKU athlete {athlete_id}"
        # El oponente gana por walkover — winner_id = the other athlete
        if m.aka_id == athlete_id:
            m.winner_id = m.ao_id
        else:
            m.winner_id = m.aka_id
        session.add(m)
```

## DB Lock Strategy

### `with_for_update()` — SQLite vs PostgreSQL

```python
def apply_penalty(match_id, participant, penalty_type, reason, applied_by_id,
                  match_time_seconds=None):
    max_retries = 3
    base_delay = 0.05  # 50ms

    for attempt in range(max_retries):
        try:
            with rx.session() as session:
                # with_for_update() es NO-OP en SQLite (serialized txn lo cubre)
                # En PostgreSQL emite SELECT ... FOR UPDATE real
                match = session.exec(
                    select(Match)
                    .where(Match.id == match_id)
                    .with_for_update()
                ).first()

                if not match:
                    raise MatchNotInProgressError(f"Match {match_id} not found")
                if match.status != MatchStatus.IN_PROGRESS.value:
                    raise MatchNotInProgressError(...)

                # ... lógica de penalty ...
                session.commit()
                return result

        except OperationalError as e:
            # SQLite: "database is locked"
            # PostgreSQL: deadlock detected
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.01)
                time.sleep(delay)
                continue
            raise ConcurrencyError(
                f"Lock acquisition failed after {max_retries} attempts"
            ) from e
```

**Explicación SQLite vs PostgreSQL**:
- **SQLite (dev)**: `with_for_update()` es ignorado. SQLite usa write-ahead logging (WAL) con un solo writer a la vez. Transacciones concurrentes se serializan automáticamente. Si dos threads intentan escribir, uno recibe `SQLITE_BUSY` → nuestro retry con backoff lo maneja.
- **PostgreSQL (prod)**: `with_for_update()` emite `SELECT ... FOR UPDATE` real que bloquea la fila del match. Otros transactions esperan hasta que el lock se libere. En caso de deadlock, PG lanza `OperationalError` → retry lo maneja.
- **Backoff exponencial**: 50ms → 100ms → 200ms con jitter aleatorio para evitar thundering herd.

**Tests de contención**:

| Test | Descripción | Approach |
|------|------------|----------|
| `test_concurrent_penalty_same_match` | 2 threads aplican penalty al mismo match_id simultáneamente | `threading.Thread` × 2, assert solo uno tiene la cuenta correcta, el otro retries o falla con `ConcurrencyError` |
| `test_retry_succeeds_after_lock` | Mock `OperationalError` en primer intento, éxito en segundo | `unittest.mock.patch` sobre session.exec para fallar 1 vez |
| `test_max_retries_exceeded` | Mock 3 fallos consecutivos → `ConcurrencyError` | Patch para fallar 3 veces, assert exception raised |
| `test_sqlite_serialized_txn` | Confirmar que SQLite serializa sin `FOR UPDATE` | 2 concurrent sessions, verify data integrity post-commit |

## Migration Steps

```bash
# 1. Generar migración
alembic revision --autogenerate -m "add_is_disqualified_and_penalty_indices"

# 2. Verificar/editar la migración generada
```

**Contenido esperado de la migración**:

```python
def upgrade():
    # Campo is_disqualified en athletes
    op.add_column('athletes',
        sa.Column('is_disqualified', sa.Boolean(),
                  nullable=False, server_default=sa.text('0')))

    # Índice compuesto en penalties para queries de contención
    op.create_index('ix_penalties_match_participant',
                    'penalties', ['match_id', 'participant'])

    # Índice para scheduling overlap queries
    op.create_index('ix_matches_tatami_start_time',
                    'matches', ['tatami_id', 'start_time'])


def downgrade():
    op.drop_index('ix_matches_tatami_start_time', table_name='matches')
    op.drop_index('ix_penalties_match_participant', table_name='penalties')
    op.drop_column('athletes', 'is_disqualified')
```

**Nota PostgreSQL**: Si se ejecuta en producción con tabla `matches` grande y activa:
```python
# Usar CREATE INDEX CONCURRENTLY para no bloquear writes
# En alembic, esto requiere:
# 1. op.execute() directo (autogenerate no soporta CONCURRENTLY)
# 2. Ejecutar FUERA de transacción (autocommit mode)

def upgrade():
    # ... add_column normal ...

    # Para PostgreSQL CONCURRENTLY:
    # op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS "
    #            "ix_penalties_match_participant "
    #            "ON penalties (match_id, participant)")
    # NOTA: Requiere connection.execution_options(isolation_level="AUTOCOMMIT")
    # en env.py de alembic, o separar en migración dedicada.
    #
    # Para SQLite (dev): usar create_index normal (sin CONCURRENTLY).
    op.create_index('ix_penalties_match_participant',
                    'penalties', ['match_id', 'participant'])
```

`match_time_seconds` ya existe en `Penalty` (línea 433 tournament_model.py) — NO requiere migración.

## Rollback / Compensation Plan

**Problema**: SHIKKAKU en RR puede modificar múltiples matches (nullificar scores, cancelar futuros). Un error humano (SHIKKAKU aplicado al atleta equivocado) necesita revertirse.

### Delta Snapshot Strategy

```python
@dataclass
class StandingsDelta:
    """Snapshot de cambios para rollback."""
    athlete_id: int
    category_id: int
    timestamp: datetime
    changes: list[dict]  # [{match_id, field, old_value, new_value}, ...]


def _capture_standings_delta(athlete_id, category_id, session) -> StandingsDelta:
    """Captura estado actual de todos los matches del atleta en la categoría
    ANTES de aplicar SHIKKAKU. Retorna delta para posible rollback."""
    matches = session.exec(
        select(Match).where(
            Match.category_id == category_id,
            or_(Match.aka_id == athlete_id, Match.ao_id == athlete_id),
        )
    ).all()

    return StandingsDelta(
        athlete_id=athlete_id,
        category_id=category_id,
        timestamp=datetime.utcnow(),
        changes=[
            {"match_id": m.id, "field": "full_state",
             "old_value": {
                 "aka_score": m.aka_score, "ao_score": m.ao_score,
                 "winner_id": m.winner_id, "status": m.status,
                 "notes": m.notes,
             }}
            for m in matches
        ],
    )


def _persist_standings_delta(delta, athlete_id, category_id, session):
    """Persiste delta como JSON en una nueva tabla o campo de auditoría.
    Opción 1: Tabla `standings_deltas` (preferida para queries).
    Opción 2: Campo `rollback_data` JSON en Athlete (simple)."""
    # Implementación: guardar como JSON serializado
    # Admin endpoint lo lee para revertir
```

### Admin Revert Endpoint

```python
@staticmethod
def revert_shikkaku(athlete_id: int, category_id: int) -> bool:
    """Admin-only: revierte SHIKKAKU leyendo el delta guardado.
    1. Lee StandingsDelta del atleta/categoría
    2. Restaura scores/status/winner de cada match afectado
    3. Limpia is_disqualified
    4. Re-activa matches cancelados (CANCELLED → PENDING)
    5. Elimina la Penalty de tipo SHIKKAKU
    Retorna True si revertido exitosamente."""
```

**Modelo de auditoría** (nueva tabla, mínima):

```python
class StandingsDeltaLog(rx.Model, table=True):
    __tablename__ = "standings_delta_logs"
    athlete_id: int = Field(foreign_key="athletes.id", index=True)
    category_id: int = Field(foreign_key="tournament_categories.id")
    delta_json: str = Field()  # JSON serializado del StandingsDelta
    applied_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    reverted_at: Optional[datetime.datetime] = Field(default=None)
    reverted_by_id: Optional[int] = Field(default=None, foreign_key="users.id")
```

## Scheduling Overlap Enforcement (PINNED)

> **⚠️ PINNED DECISIONS** — The entry point, signature, wiring, and index below are locked.
> Do not change without orchestrator approval.

**Problem**: An athlete competing in both Kata and Kumite (or multiple Kumite categories) could be assigned to two tatamis with overlapping time windows. Since `Match.tatami_id` is defined in the model but never assigned in code yet, this check must be introduced as a NEW service alongside the first tatami assignment logic.

### Entry Point (PINNED)

- **New file**: `kakumi_app/services/scheduling_service.py`
- **Function signature**:

```python
class AthleteSchedulingConflictError(PenaltyError):
    """Raised when an athlete has another active match within the gap window."""


def check_athlete_scheduling_overlap(
    session: Session,
    athlete_id: int,
    match_id: int,
    gap_seconds: int = 75,
) -> None:
    """Check that `athlete_id` has no other active match overlapping with
    the time window of `match_id` (including the gap buffer).

    Raises:
        AthleteSchedulingConflictError: if overlap is detected.

    Algorithm:
        1. Load the target match and its category to get start_time and
           match_duration_seconds.
        2. Compute the protected window:
           [start_time - gap_seconds, start_time + match_duration_seconds + gap_seconds]
        3. Query all OTHER matches of the athlete where tatami_id IS NOT NULL
           and start_time IS NOT NULL and status IN (PENDING, READY, IN_PROGRESS).
        4. For each candidate, compute its own window using its category's
           match_duration_seconds. Check overlap.
        5. Because SQLite has limited datetime functions, overlap filtering
           is done in Python using timedelta arithmetic — NOT SQL INTERVAL.
    """
    target_match = session.get(Match, match_id)
    if not target_match or not target_match.start_time:
        return  # No start_time assigned yet — nothing to check

    target_duration = target_match.category.match_duration_seconds
    target_start = target_match.start_time
    target_end = target_start + timedelta(seconds=target_duration)

    # Widen window by gap_seconds on both sides
    window_start = target_start - timedelta(seconds=gap_seconds)
    window_end = target_end + timedelta(seconds=gap_seconds)

    # Pre-filter in SQL: matches of this athlete with tatami + start_time set
    candidates = session.exec(
        select(Match).where(
            Match.id != match_id,
            Match.tatami_id.isnot(None),
            Match.start_time.isnot(None),
            Match.status.in_([
                MatchStatus.PENDING.value,
                MatchStatus.READY.value,
                MatchStatus.IN_PROGRESS.value,
            ]),
            or_(Match.aka_id == athlete_id, Match.ao_id == athlete_id),
            # Coarse SQL filter: start_time within a generous range
            Match.start_time < window_end,
        )
    ).all()

    # Fine-grained Python-side overlap check (needs each match's duration)
    for m in candidates:
        m_duration = m.category.match_duration_seconds
        m_end = m.start_time + timedelta(seconds=m_duration)
        # Overlap condition including gap:
        #   candidate.start < window_end AND candidate.end > window_start
        if m.start_time < window_end and m_end > window_start:
            raise AthleteSchedulingConflictError(
                f"Athlete {athlete_id} has overlapping match {m.id} "
                f"on tatami {m.tatami_id} "
                f"({m.start_time} - {m_end}) within {gap_seconds}s gap"
            )
```

### Called From (PINNED)

**`kumite_scoring_service.apply_penalty()`** — called BEFORE committing any penalty, as a guard to ensure the penalized athlete's match doesn't conflict with another active match on a different tatami. This enforces the constraint at the service boundary where match state transitions happen.

### Wiring Diagram (PINNED)

```
apply_penalty(session, match_id, participant_id, penalty_type)
  │
  ├─► check_athlete_scheduling_overlap(session, athlete_id, match_id, gap_seconds)
  │       raises AthleteSchedulingConflictError → abort, no penalty written
  │
  ├─► [acquire with_for_update lock on Match row]
  ├─► [compute escalation]
  ├─► [write Penalty row]
  ├─► [if SHIKKAKU → _apply_shikkaku_round_robin()]
  └─► [write StandingsDeltaLog snapshot]
```

### Gap Seconds Configuration (PINNED)

- **Default**: `75` seconds (midpoint of the 60–90s WKF recommended range between matches)
- **Overridable per tournament**: Add `scheduling_gap_seconds: int = Field(default=75)` to the `Tournament` model
- The `apply_penalty()` caller reads `tournament.scheduling_gap_seconds` and passes it to the check function

### Model Change Required

```python
# In Tournament model (tournament_model.py)
scheduling_gap_seconds: int = Field(default=75)
```

### Index (PINNED)

- **Name**: `ix_matches_tatami_start_time`
- **Columns**: `(tatami_id, start_time)` on the `matches` table
- **Purpose**: Performance for the overlap query that filters by `tatami_id IS NOT NULL` and `start_time` range
- Already included in the migration plan (see Migration Steps section)

### SQLite Note (PINNED)

SQLite does not support `INTERVAL` or datetime arithmetic in SQL. All time window calculations MUST use Python `datetime.timedelta` for filtering. The SQL query only does coarse pre-filtering (`Match.start_time < window_end`); the precise overlap check with `match_duration_seconds + gap_seconds` happens in Python.

### Tests de Scheduling

| Test | Description |
|------|------------|
| `test_no_overlap_different_times` | Two matches of same athlete on different tatamis, no overlap → passes |
| `test_overlap_same_athlete_two_tatamis` | Match A: 10:00-10:03, Match B: 10:02-10:05 → `AthleteSchedulingConflictError` |
| `test_adjacent_no_overlap` | Match A: 10:00-10:03, Match B: 10:03+gap → OK (respects gap boundary) |
| `test_overlap_within_gap_seconds` | Match ends at 10:03, next starts at 10:04 with gap=75s → conflict |
| `test_overlap_check_both_participants` | aka_id of match A = ao_id of match B, times overlap → conflict |
| `test_reassign_excludes_self` | Re-assign existing match to another tatami, excludes own ID → OK |
| `test_completed_match_ignored` | COMPLETED match does not block assignment → OK |
| `test_no_start_time_skips_check` | Match without start_time → check returns without error |
| `test_custom_gap_seconds` | Tournament with `scheduling_gap_seconds=120` → wider conflict window |

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `kakumi_app/models/athlete_model.py` | Modify | Add `is_disqualified: bool = Field(default=False)` |
| `kakumi_app/models/tournament_model.py` | Modify | Add index on `(match_id, participant)` en Penalty, add `StandingsDeltaLog` model |
| `kakumi_app/services/kumite_scoring_service.py` | Modify | Add `with_for_update()` + retry, `_apply_shikkaku_round_robin()`, `_is_last_rr_match()`, `_nullify_rr_previous_scores()`, `_cancel_remaining_rr_matches()`, `_capture_standings_delta()`, `_persist_standings_delta()`, `revert_shikkaku()`, `remove_last_penalty()` |
| `kakumi_app/services/exceptions.py` | Create | `PenaltyError`, `MatchNotInProgressError`, `ConcurrencyError`, `PenaltyRemovalNotAllowedError`, `ShikkakuRoundRobinError`, `AthleteSchedulingConflictError` |
| `kakumi_app/services/scheduling_service.py` | Create | `check_athlete_scheduling_overlap(session, athlete_id, match_id, gap_seconds)` — PINNED entry point |
| `kakumi_app/models/tournament_model.py` | Modify | Add index on `(match_id, participant)` en Penalty, add `StandingsDeltaLog` model, add `scheduling_gap_seconds` to Tournament |
| `kakumi_app/states/kumite_match_state.py` | Create | `KumiteMatchState(rx.State)` — timer vars, penalty handlers |
| `alembic/versions/xxx_add_penalty_system.py` | Create | Migration: `is_disqualified`, indices, `standings_delta_logs` |
| `tests/test_penalty_system.py` | Create | Unit + integration tests (TDD: tests FIRST) |
| `tests/test_scheduling_overlap.py` | Create | Scheduling constraint tests (TDD) |
| `tests/test_concurrency.py` | Create | Lock contention tests |
| `tests/conftest.py` | Modify | Fixtures for match + penalties + RR schedule + tatami |

## Interfaces / Contracts

```python
# exceptions.py
class PenaltyError(Exception): ...
class MatchNotInProgressError(PenaltyError): ...
class ConcurrencyError(PenaltyError): ...
class PenaltyRemovalNotAllowedError(PenaltyError): ...
class ShikkakuRoundRobinError(PenaltyError): ...
class SchedulingConflictError(PenaltyError): ...

# KumiteScoringService
@staticmethod
def apply_penalty(match_id, participant, penalty_type, reason,
                  applied_by_id, match_time_seconds=None) -> PenaltyResult: ...

@staticmethod
def _apply_shikkaku_round_robin(match, penalized_participant, session) -> None: ...

@staticmethod
def _is_last_rr_match(match, athlete_id, session) -> bool: ...

@staticmethod
def _nullify_rr_previous_scores(athlete_id, category_id, current_match_id, session) -> None: ...

@staticmethod
def _cancel_remaining_rr_matches(athlete_id, category_id, current_match_id, session) -> None: ...

@staticmethod
def remove_last_penalty(match_id, participant) -> PenaltyResult: ...

@staticmethod
def revert_shikkaku(athlete_id, category_id) -> bool: ...

# Scheduling
class AthleteSchedulingConflictError(PenaltyError): ...

def check_athlete_scheduling_overlap(session: Session, athlete_id: int,
    match_id: int, gap_seconds: int = 75) -> None: ...
    # Raises AthleteSchedulingConflictError on overlap

# KumiteMatchState (Reflex)
class KumiteMatchState(rx.State):
    current_match_id: int = 0
    timer_running: bool = False
    timer_seconds: int = 0
    aka_penalties: list[dict] = []
    ao_penalties: list[dict] = []

    async def handle_apply_penalty(self, participant, penalty_type, reason) -> None: ...
    async def handle_remove_penalty(self, participant) -> None: ...
```

## Testing Strategy

> **TDD**: Tests se escriben ANTES que la implementación. Cada PR debe incluir tests en el primer commit.

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Escalation CHUI→HANSOKU_CHUI→HANSOKU | Parametrize penalty sequences |
| Unit | SHIKKAKU sets `is_disqualified=True` | Mock session, verify flag |
| Unit | `remove_last_penalty` de-escalation | Apply 3 CHUI, remove 1, verify |
| Unit | `remove_last_penalty` on COMPLETED/CANCELLED | Assert `PenaltyRemovalNotAllowedError` |
| Unit | SHIKKAKU RR último encuentro individual | Scores PRESERVED, DQ'd, future cancelled |
| Unit | SHIKKAKU RR no-último encuentro individual | Scores NULLIFIED, DQ'd, future cancelled |
| Unit | SHIKKAKU RR último encuentro equipos | Scores PRESERVED, team result per WKF |
| Unit | SHIKKAKU RR no-último encuentro equipos | Scores NULLIFIED, team result per WKF |
| Unit | `_is_last_rr_match` true/false | Fixtures con matches COMPLETED vs PENDING |
| Unit | `_nullify_rr_previous_scores` | Verify scores zeroed, notes updated |
| Unit | `_cancel_remaining_rr_matches` | Verify CANCELLED status, winner assigned |
| Unit | Scheduling overlap detection | 6 cases: no overlap, overlap, adjacent, both participants, reassign, completed |
| Unit | `revert_shikkaku` rollback | Apply SHIKKAKU, revert, verify original state |
| Unit | `StandingsDelta` capture/persist | Verify JSON roundtrip fidelity |
| Integration | Concurrent double-penalty | 2 threads same match_id, lock contention |
| Integration | Retry after lock timeout | Mock OperationalError, verify backoff |
| Integration | Max retries exceeded | 3 failures → `ConcurrencyError` |
| Integration | HANSOKU RR vs elimination | Fixtures per competition_system |
| Edge | Penalty on COMPLETED match | `MatchNotInProgressError` |

## Migration / Rollout

1. **Pre-flight**: Backup `kakumi.db` antes de migrar.
2. **Migration**: `alembic revision --autogenerate -m "add_penalty_system_fields"` → `alembic upgrade head`.
3. **Post-migration**: Verificar `is_disqualified` column con `SELECT * FROM athletes LIMIT 1`.
4. **PostgreSQL prod**: Usar `CREATE INDEX CONCURRENTLY` para índices en tablas con tráfico (ver sección Migration Steps).
5. **Rollback DB**: `alembic downgrade -1` revierte columna e índices.

## Open Questions

- [x] ~~¿SHIKKAKU en RR anula scores anteriores?~~ **RESUELTO**: Depende de último/no-último (Art. 10.7.2).
- [x] ~~¿`remove_last_penalty` post-COMPLETED?~~ **RESUELTO**: NO. Guard clause.
- [ ] ¿`StandingsDeltaLog` justifica tabla nueva o campo JSON en `Athlete`? → Tabla nueva preferida para auditabilidad. Decidir en tasks.
- [x] ~~¿Buffer temporal entre matches para scheduling?~~ **RESUELTO**: 75s default (midpoint 60-90s WKF range), configurable via `Tournament.scheduling_gap_seconds`. PINNED.
