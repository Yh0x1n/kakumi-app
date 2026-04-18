# Exploration: Penalty System (WKF 2026)

## Current State

Sistema Kumite existe con scoring básico. `PenaltyType` enum tiene: CHUI, HANSOKU_CHUI, HANSOKU, SHIKKAKU. Modelo `Penalty` persiste con `participant`, `penalty_type`, `reason`, `is_accumulated`, `rule_reference`.

Service `KumiteScoringService.apply_penalty()` implementa escalación:
- 3 CHUI máx → 4to = HANSOKU_CHUI
- HANSOKU_CHUI previo + nueva CHUI = HANSOKU
- HANSOKU directo → termina match, YUKO al rival

Tests cubren: escalación CHUI→HANSOKU_CHUI, HANSOKU termina, round-robin 4-0 rule.

## Gaps Identified

### 1. SHIKKAKU Sin Implementar
- Enum existe, pero `apply_penalty` NO procesa SHIKKAKU
- WKF Art. X: SHIKKAKU = descalificación total torneo, no solo match
- Falta lógica: flag `is_tournament_dq` en modelo, efecto en standings

### 2. Direct Penalties
- WKF: faltas graves pueden recibir HANSOKU_CHUI/HANSOKU directo
- Service actual solo escala desde CHUI
- Falta: parámetro `direct=True` o validación de penalty_type inicial

### 3. BOTH Participant
- `ParticipantSide.BOTH` existe en enum
- Service usa `Participant` (AKA/AO) no `ParticipantSide`
- Penalidades simultáneas a ambos (excessive contact mutuo) no implementadas

### 4. Rule Reference Field
- Campo `rule_reference` existe pero nunca se usa
- Falta validación contra WKF Article numbers

### 5. Match Time Tracking
- Campo `match_time_seconds` existe, no se popula
- WKF: tiempo de penalidad relevante para decisions

### 6. Category Penalty Limits
- WKF: max penalidades antes de SHIKKAKU no implementado
- Falta tracking de strikes累计 por categoría

### 7. UI/State para Operador
- Sin estado ni componentes para operar penalidades desde UI
- Solo backend service existe

### 8. Tests Faltantes
- SHIKKAKU scenario
- BOTH participant scenario
- Direct HANSOKU_CHUI/HANSOKU
- Validation rule_reference
- Match time recording
- Revoke/modify penalty
- Edge cases: penalties on completed match, concurrent penalties

## Affected Areas

| Archivo | Impacto |
|---------|---------|
| `kakumi_app/models/tournament_model.py` | Modelo Penalty: add `is_direct`, `is_tournament_disqualification` |
| `kakumi_app/services/kumite_scoring_service.py` | `apply_penalty`: SHIKKAKU, BOTH, direct, match_time |
| `kakumi_app/states/` (nuevo) | Estado UI para operador si aplica |
| `tests/test_kumite_scoring_service.py` | Tests nuevos para gaps |
| `alembic/versions/` | Migración: add fields a Penalty |

## Approaches

### Opción A: Full Implementation
**Scope**: SHIKKAKU, BOTH, direct penalties, UI state
- Pros: Sistema completo WKF 2026
- Cons: Alto esfuerzo, muchas dependencias
- Effort: HIGH

### Opción B: Core Penalties Only
**Scope**: SHIKKAKU, direct penalties, time tracking
- Pros: Cierra gaps críticos, testing enfocado
- Cons: BOTH y UI quedan para otro change
- Effort: MEDIUM

### Opción C: Minimal Viable
**Scope**: Solo SHIKKAKU + direct penalties
- Pros: Quick win, sin UI
- Cons: Débt técnico acumula
- Effort: LOW

## Recommendation

**Opción B**: Core Penalties Only.

Justificación:
- SHIKKAKU es gap crítico (enum existe sin uso)
- Direct penalties es funcionalidad WKF esperada
- BOTH participant requiere refactoring más profundo
- UI state es change separado (sigue Python-only rule, pero out of scope)

## Risks

1. **SHIKKAKU scope**: Afecta standings de categoría, requiere investigación impacto
2. **Match time**: `match_time_seconds` en Penalty, pero Match no tiene timer
3. **Concurrent penalties**: Race condition si operadores aplican simultáneo
4. **Round-robin edge cases**: SHIKKAKU en round-robin tiene reglas diferentes
5. **Breaking change**: Si Penalty model cambia, tests existentes pueden romper

## Ready for Proposal

**Yes**. Scope claro: implementar SHIKKAKU, direct penalties, time tracking en service + tests. BOTH y UI quedan out of scope para follow-up.

## Dependencies

- `kumite-scoring-system` (archived): ya implementó CHUI→HANSOKU_CHUI→HANSOKU
- WKF 2026 PDF: Art. 10.6.1, 10.7.1 (SHIKKAKU rules)
- `Penalty` model: ya tiene campos necesarios, solo populate