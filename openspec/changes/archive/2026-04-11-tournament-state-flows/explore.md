# Exploration: Flujos de estado de torneo

## Objetivo
Implementar transiciones de estado de torneo (PLANIFICADO → INSCRIPCION → VERIFICACION → EN_CURSO → FINALIZADO → ARCHIVADO) con validaciones y lógica de negocio.

## Current State

### Modelo ya definido
El modelo `Tournament` en `kakumi_app/models/tournament_model.py` (líneas 109-140):
- Ya tiene el enum `TournamentStatus` con los 6 estados requeridos
- Ya tiene el campo `status: str = Field(default=TournamentStatus.PLANIFICADO.value)`
- Los tests en `tests/test_models_base.py` verifican el enum y transiciones básicas

### Qué falta por implementar
1. **No existe lógica de validación de transiciones** — actualmente se puede cambiar de cualquier estado a cualquier otro
2. **No existe `TournamentState`** — no hay state class para gestionar torneos
3. **No existe `TournamentService`** — no hay servicio con lógica de negocio
4. **RBAC tiene el permiso** `MANAGE_TOURNAMENT_STATUS` pero no se usa

### Especificación en specs.md (sección 6.1-6.2)

| Desde | Hacia | Condición |
|-------|-------|-----------|
| PLANIFICADO | INSCRIPCION | OPERATOR/ADMIN ejecuta "Abrir inscripciones" |
| INSCRIPCION | VERIFICACION | Cierre automático o manual |
| VERIFICACION | EN_CURSO | ADMIN ejecuta "Iniciar competición" |
| EN_CURSO | FINALIZADO | Todas las categorías completadas |
| FINALIZADO | ARCHIVADO | ADMIN ejecuta "Archivar torneo" |
| Cualquiera | PLANIFICADO | ADMIN ejecuta "Cancelar/Reiniciar" (sin encuentros activos) |

## Affected Areas

- `kakumi_app/models/tournament_model.py` — Agregar método de validación de transiciones
- `kakumi_app/states/` — Crear `tournament_state.py` con lógica de transición
- `kakumi_app/services/` — Crear `tournament_service.py` (lógica de negocio reusable)
- `kakumi_app/pages/admin/tournaments_page.py` — Crear UI para gestión de estados
- `kakumi_app/auth/rbac.py` — Ya tiene el permiso, solo necesita integración
- `tests/test_models_base.py` — Tests existentes verifican enum, falta tests de transición

## Approaches

### 1. State-only Approach
Implementar toda la lógica de transición dentro de `TournamentState` (como hace `AthleteState`).

- **Pros**: Simple, seguir el patrón existente del proyecto
- **Cons**: Lógica de negocio duplicable si se necesita desde CLI/API
- **Effort**: Medium

### 2. Service-first Approach (RECOMENDADO)
Crear `TournamentService` con método `transition_status()` y reglas de validación, luego usar desde `TournamentState`.

```python
class TournamentService:
    @staticmethod
    def can_transition(from_status: str, to_status: str, context: dict) -> bool:
        # Validaciones según specs.md 6.2
        pass
    
    @staticmethod
    def execute_transition(tournament_id: int, to_status: str) -> Result:
        # Validar, actualizar, loggear
        pass
```

- **Pros**: Separación de concerns, reusable desde CLI/API/tests, testable aisladamente
- **Cons**: Un poco más de código inicial
- **Effort**: Medium-High

### 3. FSM Library Approach
Usar una biblioteca como `transitions` o `python-statemachine`.

- **Pros**: Framework maduro, validaciones automáticas
- **Cons**: Dependencia adicional, overkill para 6 estados simples
- **Effort**: High (setup + learning curve)

## Recommendation

**Approach 2 (Service-first)** es la mejor opción porque:

1. **Separación clara**: La lógica de negocio no debería vivir en un State de Reflex
2. **Testabilidad**: Se pueden unittestear las transiciones sin UI
3. **Reusabilidad**: Si mañana se necesita una API REST o CLI, el servicio es el mismo
4. **Patrón consistente**: Similar a `AuthService`, `ExportService`, etc. ya existentes
5. **Escala**: Si las reglas de transición se vuelven complejas, el servicio las contiene

### Implementación sugerida

1. Crear `TournamentService` con:
   - `VALID_TRANSITIONS: dict` — mapa de transiciones válidas
   - `can_transition(tournament, new_status)` — valida sin ejecutar
   - `transition_to(tournament_id, new_status)` — ejecuta con validaciones

2. Crear `TournamentState` que use el servicio:
   - Métodos: `open_registrations()`, `close_registrations()`, `start_competition()`, `finish_competition()`, `archive_tournament()`, `cancel_tournament()`
   - Cada método llama a `TournamentService.transition_to()`

3. Crear `pages/admin/tournaments_page.py` con:
   - Listado de torneos con estado visual
   - Botones de acción según estado y permisos
   - Confirmaciones para transiciones destructivas

## Risks

- **Risk**: Transiciones inválidas permitidas actualmente — Si se hace deploy así, usuarios podrían romper el flujo
- **Risk**: Dependencias de estado — Al pasar a EN_CURSO, todas las categorías deben estar en READY
- **Risk**: Integración con RBAC — El permiso `MANAGE_TOURNAMENT_STATUS` debe requerir ADMIN para ciertas transiciones (EN_CURSO → FINALIZADO)

## Next Steps

1. Escribir specs detallados en `openspec/changes/tournament-state-flows/spec.md`
2. Diseñar arquitectura en `openspec/changes/tournament-state-flows/design.md`
3. Descomponer tareas en `openspec/changes/tournament-state-flows/tasks.md`

## Ready for Proposal

**Yes** — La exploración está completa. El modelo base existe, las especificaciones están claras en `specs.md`, y el approach recomendado (Service-first) es apropiado para el proyecto.

---
*Artifact: sdd/tournament-state-flows/explore*
*Generated: 2026-04-10*
