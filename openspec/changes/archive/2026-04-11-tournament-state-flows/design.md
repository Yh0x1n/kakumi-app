# Design: Flujos de estado de torneo

## Technical Approach

Service-first con TournamentService + TournamentState, siguiendo el patrón establecido por AuthService/AuthState.

El TournamentService centraliza toda la lógica de negocio (validaciones y transiciones) mientras TournamentState expone los event handlers para la UI de Reflex.

## Architecture Decisions

| Decision | Option A | Option B | Choice | Rationale |
|----------|----------|----------|--------|-----------|
| Dónde vive la lógica | Service puro | Métodos en Model | Service | Consistente con AuthService, testeable, desacoplado de DB |
| Exponer transiciones | Métodos individuales (open_registrations, etc.) | Método genérico (transition_to) | Ambos | Service usa genérico con validación; State expone métodos semánticos para UI |
| Validación de pre-condiciones | Inline en transition_to | Método separado validate_transition() | Separado | Permite dry-run y feedback específico antes de ejecutar |
| Valid transitions | Dict en Service | Tabla DB dinámica | Dict en Service | Reglas estáticas WKF, no requieren configuración runtime |
| Resultado de transición | Tuple (success, error) | Clase TransitionResult | Clase | Más expresivo, permite extender con warnings/audit |
| Lock de transición | Flag en Tournament | Memoria (State) | Flag en Tournament | Evita race conditions entre instancias |

## Data Flow

```
User Click
    │
    ▼
TournamentState.open_registrations()
    │
    ▼
TournamentService.can_transition() ──► VALID_TRANSITIONS table lookup
    │                                          │
    ▼                                          │
TournamentService.validate_preconditions() ◄─────┘
    │
    ▼
TournamentService.transition_to()
    │
    ├─► DB: UPDATE tournament.status
    ├─► DB: INSERT tournament_event_log
    └─► TournamentState: update local state
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `kakumi_app/services/tournament_service.py` | Create | Lógica de transiciones y validaciones |
| `kakumi_app/states/tournament_state.py` | Create | Event handlers para UI |
| `kakumi_app/models/tournament_model.py` | Modify | Agregar is_transitioning flag |
| `kakumi_app/models/tournament_event_log.py` | Create | Auditoría de cambios de estado |

## Interfaces

### TournamentService

```python
VALID_TRANSITIONS: dict[TournamentStatus, list[TournamentStatus]] = {
    TournamentStatus.PLANIFICADO: [
        TournamentStatus.INSCRIPCION,
        TournamentStatus.ARCHIVADO,
    ],
    TournamentStatus.INSCRIPCION: [
        TournamentStatus.VERIFICACION,
        TournamentStatus.PLANIFICADO,
    ],
    TournamentStatus.VERIFICACION: [
        TournamentStatus.EN_CURSO,
    ],
    TournamentStatus.EN_CURSO: [
        TournamentStatus.FINALIZADO,
    ],
    TournamentStatus.FINALIZADO: [
        TournamentStatus.ARCHIVADO,
    ],
}

class TransitionResult:
    success: bool
    tournament_id: int
    old_status: TournamentStatus
    new_status: TournamentStatus | None
    error_code: str | None  # INVALID_TRANSITION, NO_CATEGORIES, etc.
    error_message: str | None
    warnings: list[Warning]
    timestamp: datetime

@staticmethod
def can_transition(
    from_status: TournamentStatus,
    to_status: TournamentStatus
) -> bool:
    ...

@staticmethod
def validate_preconditions(
    tournament_id: int,
    to_status: TournamentStatus
) -> ValidationResult:
    """Valida pre-condiciones sin ejecutar transición (dry-run)."""
    ...

@staticmethod
def transition_to(
    tournament_id: int,
    new_status: TournamentStatus,
    user_id: int,
    dry_run: bool = False
) -> TransitionResult:
    ...
```

### TournamentState

```python
class TournamentState(rx.State):
    current_tournament: Tournament | None = None
    transition_error: str = ""
    is_transitioning: bool = False
    validation_warnings: list[str] = []

    async def open_registrations(self) -> None:
        """PLANIFICADO -> INSCRIPCION"""
        ...

    async def close_registrations(self) -> None:
        """INSCRIPCION -> VERIFICACION"""
        ...

    async def start_competition(self) -> None:
        """VERIFICACION -> EN_CURSO"""
        ...

    async def finish_competition(self) -> None:
        """EN_CURSO -> FINALIZADO"""
        ...

    async def archive_tournament(self) -> None:
        """[ANY] -> ARCHIVADO (ADMIN only)"""
        ...

    async def cancel_tournament(self) -> None:
        """PLANIFICADO -> ARCHIVADO (ADMIN only)"""
        ...

    async def reopen_registrations(self) -> None:
        """INSCRIPCION -> PLANIFICADO"""
        ...
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | `can_transition()` con todas las combinaciones | Tabla-driven tests con parametrización pytest |
| Unit | `validate_preconditions()` cada regla | Mock de DB, testear cada validator individual |
| Integration | Transición completa con DB | rx.session(), setup fixtures de tournament/categories |
| Integration | RBAC - solo ADMIN archiva | Test con user ADMIN vs OPERATOR |
| E2E | Flujo completo vía UI | No aplica (sin UI en este change) |

## Migration

No migration de datos requerida. Estados existentes en DB son válidos.

### Schema Changes

```sql
-- Agregar flag de transición en progreso
ALTER TABLE tournaments ADD COLUMN is_transitioning BOOLEAN DEFAULT FALSE;

-- Crear tabla de auditoría
CREATE TABLE tournament_event_logs (
    id INTEGER PRIMARY KEY,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id),
    user_id INTEGER REFERENCES users(id),
    event_type VARCHAR(50) NOT NULL,
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Îndice para queries de historial por torneo (requerido)
CREATE INDEX idx_tournament_event_logs_tournament_id ON tournament_event_logs(tournament_id);
```

## Open Questions

- [x] ¿Necesitamos índice en tournament_event_logs por tournament_id? **SÍ** — necesario para queries de historial
- [x] ¿TTL para logs de auditoría o mantener indefinidamente? **Indefinidamente** — requerido para WKF compliance

---

*Artifact: design*  
*Change: tournament-state-flows*  
*Type: architecture*
