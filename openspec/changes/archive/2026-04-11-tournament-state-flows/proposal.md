# Proposal: Flujos de estado de torneo

## Intent

El sistema permite transiciones de estado inválidas (cualquiera → cualquiera) violando reglas de negocio WKF para torneos de karate. Esto puede causar inconsistencias como iniciar torneos sin categorías ready o archivar torneos en curso.

## Scope

### In Scope
- TournamentService con validación de transiciones según tabla WKF
- TournamentState con event handlers para cada transición
- Validación de integridad referencial antes de transiciones críticas
- Integración RBAC con permiso MANAGE_TOURNAMENT_STATUS

### Out of Scope
- UI de visualización de brackets (change separado)
- Sistema de notificaciones de cambio de estado
- Historial/auditoría de cambios de estado

## Capabilities

### New Capabilities
- `tournament-state-transitions`: Cambio de estado con validación según tabla de transiciones WKF 2026
- `tournament-state-validation`: Pre-condiciones antes de transiciones críticas (categorias, árbitros, atletas)

### Modified Capabilities
- None (nueva funcionalidad)

## Approach

Service-first architecture:

1. **TournamentService** con:
   - `VALID_TRANSITIONS: dict` — mapa de transiciones válidas
   - `can_transition(tournament, new_status) -> bool`
   - `transition_to(tournament_id, new_status) -> Result`

2. **TournamentState** con métodos:
   - `open_registrations()`, `close_registrations()`
   - `start_competition()`, `finish_competition()`
   - `archive_tournament()`, `cancel_tournament()`

3. **RBAC integration**: Solo ADMIN puede cancelar/archivar

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `kakumi_app/services/tournament_service.py` | New | Lógica de validación y transición |
| `kakumi_app/states/tournament_state.py` | New | Event handlers para UI |
| `kakumi_app/pages/admin/tournaments_page.py` | New | UI de gestión de torneos |
| `kakumi_app/models/tournament_model.py` | Modified | Helper de validación |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Transiciones inválidas en DB existente | High | Implementar validación antes de UI |
| Dependencias entre estados (cat ready) | Medium | Validar en service layer |
| Permisos RBAC incorrectos | Low | Tests de autorización |

## Rollback Plan

1. Eliminar TournamentService y TournamentState
2. Revertir cambios en tournament_model.py
3. TournamentStatus enum permanece (no breaking change)

## Dependencies

- authentication-system SDD (completo) — User y RBAC disponibles

## Success Criteria

- [ ] Tests validan transiciones válidas e inválidas
- [ ] `can_transition()` retorna False para transiciones inválidas
- [ ] Transición a EN_CURSO falla si categorías no están ready
- [ ] Solo ADMIN puede cancelar/archivar torneos

---
*Artifact: proposal*
*Change: tournament-state-flows*
*Generated: 2026-04-10*