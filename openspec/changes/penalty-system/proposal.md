# Proposal: Penalty System (Kumite)

## Intent
Implementar WKF 2026 penalty system (Chui, Hansoku Chui, Hansoku, Shikkaku).

## Scope

### In Scope
- Asignar penalidades Kumite.
- Shikkaku → descalifica todo torneo.
- Shikkaku RR → anula resultados descalificado (salvo en último combate). Para otros en RR, solo anula match vs infractor.
- Atleta → no compite 2 tatamis simultáneos.
- `remove_last_penalty` → solo match `IN_PROGRESS`.
- Reloj stop on penalty.

### Out of Scope
- Penalidades Kata.

## Capabilities

### New Capabilities
None

### Modified Capabilities
- `kumite-scoring-system`: RR Shikkaku logic.
- `tournament-state-transitions`: `remove_last_penalty` status check.
- `tournament-state-validation`: un tatami por atleta.

## Approach
Reusar `Penalty`. Add `is_disqualified` en `Athlete`. Actualizar `kumite_scoring_service` con reglas WKF. SQLModel tx. Validar state y tatami on mutations. TDD estricto (`strict_tdd: true`).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `kakumi_app/models/` | Modified | Add `is_disqualified` a `Athlete` |
| `kakumi_app/services/` | Modified | Lógica WKF Shikkaku RR |
| `kakumi_app/states.py` | Modified | Validar single tatami, undo guard |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Inconsistencia RR | Med | Unit tests TDD Shikkaku RR |
| Doble tatami race | Med | DB tx lock y pre-check |
| Undo post-match | Low | Guard `IN_PROGRESS` |

## Rollback Plan
Alembic downgrade. Revert git commit.

## Dependencies
- DB esquema actual.

## Success Criteria
- [ ] UI asigna penalidades.
- [ ] Shikkaku anula resultados RR correcto.
- [ ] `remove_last_penalty` falla match no `IN_PROGRESS`.
- [ ] Atleta no en 2 tatamis.
- [ ] Concurrencia segura.
