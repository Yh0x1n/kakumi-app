# Spec: Tournament State Transitions

## Overview

Domain: Tournament State Management  
Capability: `tournament-state-transitions`  
Change: tournament-state-flows

## Purpose

Definir las reglas de transición de estado válidas para torneos de karate según regulaciones WKF 2026. El sistema debe permitir solo transiciones que cumplan con la tabla de transiciones válidas y rechazar intentos de transición inválidos con feedback apropiado.

## Requirements

### Core Requirements

1. **MUST** permitir transición de PLANIFICADO a INSCRIPCION
2. **MUST** permitir transición de INSCRIPCION a VERIFICACION
3. **MUST** permitir transición de VERIFICACION a EN_CURSO
4. **MUST** permitir transición de EN_CURSO a FINALIZADO
5. **MUST** permitir transición de FINALIZADO a ARCHIVADO
6. **MUST** permitir transición de PLANIFICADO a ARCHIVADO (cancelar torneo)
7. **MUST** permitir transición de INSCRIPCION a PLANIFICADO (reabrir inscripciones)
8. **MUST** rechazar transición de EN_CURSO a INSCRIPCION con error apropiado
9. **MUST** rechazar cualquier transición hacia estados que no estén en la tabla de transiciones válidas
10. **MUST** retornar error con código y mensaje cuando transición sea inválida

### Integration Requirements

11. **SHALL** integrate con TournamentService.can_transition() para validación
12. **SHALL** llamar a TournamentEventLog para auditar transiciones exitosas
13. **SHOULD** loguear intentos de transición inválida para auditoría de seguridad
14. **MAY** implementar restricciones adicionales por rol de usuario

## Valid Transitions Table

| From State | To State | Allowed | Reason |
|-----------|---------|---------|--------|
| PLANIFICADO | INSCRIPCION | Yes | Apertura de inscripciones |
| PLANIFICADO | ARCHIVADO | Yes | Cancelar torneo |
| INSCRIPCION | VERIFICACION | Yes | Cerrar inscripciones, verificar atletas |
| INSCRIPCION | PLANIFICADO | Yes | Reabrir inscripciones |
| VERIFICACION | EN_CURSO | Yes | Iniciar competencia |
| EN_CURSO | FINALIZADO | Yes | Finalizar competencia |
| FINALIZADO | ARCHIVADO | Yes | Archivar resultados |
| EN_CURSO | INSCRIPCION | **No** | Debe finalizar primero |
| EN_CURSO | PLANIFICADO | **No** | Debe finalizar primero |
| EN_CURSO | VERIFICACION | **No** | Debe finalizar primero |
| FINALIZADO | EN_CURSO | **No** | No se puede reopen competencia finalizada |
| FINALIZADO | VERIFICACION | **No** | No se puede reopen |
| FINALIZADO | INSCRIPCION | **No** | No se puede reopen |
| FINALIZADO | PLANIFICADO | **No** | No se puede reopen |
| ARCHIVADO | * | **No** | Estado terminal |
| VERIFICACION | PLANIFICADO | **No** | Debe iniciar o archivar |

## Scenarios

### Happy Paths

#### Scenario: Open Registrations

**Given** un torneo en estado PLANIFICADO  
**When** el administrador ejecuta transición a INSCRIPCION  
**Then** el sistema debe cambiar el estado del torneo a INSCRIPCION  
**And** debe retornar éxito con el nuevo estado

#### Scenario: Start Competition

**Given** un torneo en estado VERIFICACION  
**And** todas las categorías tienen atletas suficientes para competencia  
**When** el administrador ejecuta transición a EN_CURSO  
**Then** el sistema debe cambiar el estado del tournament a EN_CURSO  
**And** debe retornar éxito con el nuevo estado

#### Scenario: Complete Tournament

**Given** un torneo en estado EN_CURSO  
**And** todos los matches están completados  
**When** el administrador ejecuta transición a FINALIZADO  
**Then** el sistema debe cambiar el estado del torneo a FINALIZADO  
**And** debe retornar éxito con el nuevo estado

#### Scenario: Reopen Registrations

**Given** un torneo en estado INSCRIPCION  
**When** el administrador ejecuta transición a PLANIFICADO  
**Then** el sistema debe cambiar el estado del torneo a PLANIFICADO  
**And** debe retornar éxito con el nuevo estado

#### Scenario: Cancel Tournament

**Given** un torneo en estado PLANIFICADO  
**When** el administrador ejecuta transición a ARCHIVADO  
**Then** el sistema debe cambiar el estado del torneo a ARCHIVADO  
**And** debe retornar éxito con el nuevo estado

### Edge Cases

#### Scenario: Try to Transition from In-Course to Registration

**Given** un torneo en estado EN_CURSO  
**When** el administrador intenta ejecutar transición a INSCRIPCION  
**Then** el sistema debe rechazar la transición  
**And** debe retornar error con código INVALID_TRANSITION  
**And** debe incluir mensaje indicando que debe finalizar primero

#### Scenario: Try to Transition from Finished to In-Course

**Given** un torneo en estado FINALIZADO  
**When** el administrador intenta ejecutar transición a EN_CURSO  
**Then** el sistema debe rechazar la transición  
**And** debe retornar error con código INVALID_TRANSITION  
**And** debe incluir mensaje indicando que no se puede reopen competencia finalizada

#### Scenario: Try to Transition from Archived

**Given** un tournament en estado ARCHIVADO  
**When** cualquier usuario intenta ejecutar transición a cualquier estado  
**Then** el sistema debe rechazar la transición  
**And** debe retornar error con código TERMINAL_STATE  
**And** debe incluir mensaje indicando que estado ARCHIVADO es terminal

#### Scenario: Try Invalid Transition from Verification

**Given** un torneo en estado VERIFICACION  
**When** el administrador intenta ejecutar transición a PLANIFICADO  
**Then** el sistema debe rechazar la transición  
**And** debe retornar error con código INVALID_TRANSITION  
**And** debe incluir mensaje indicando las opciones válidas

#### Scenario: Transition with Invalid Current State

**Given** el estado actual del torneo es null o inválido  
**When** se intenta ejecutar cualquier transición  
**Then** el sistema debe rechazar la transición  
**And** debe retornar error con código INVALID_CURRENT_STATE

#### Scenario: Double Transition Attempt

**Given** un torneo en transición desde PLANIFICADO a INSCRIPCION  
**When** se intenta otra transición simultánea  
**Then** el sistema debe rechazar la segunda transición  
**And** debe retornar error con código TRANSITION_IN_PROGRESS

## Data Model

### Tournament Status Enum

```python
class TournamentStatus(str, Enum):
    PLANIFICADO = "PLANIFICADO"
    INSCRIPCION = "INSCRIPCION"
    VERIFICACION = "VERIFICACION"
    EN_CURSO = "EN_CURSO"
    FINALIZADO = "FINALIZADO"
    ARCHIVADO = "ARCHIVADO"
```

### Transition Result

```python
class TransitionResult:
    success: bool
    tournament_id: int
    old_status: TournamentStatus
    new_status: TournamentStatus | None
    error_code: str | None
    error_message: str | None
    timestamp: datetime
```

## Acceptance Criteria

1. Todas las transiciones válidas de la tabla deben ser permitidas
2. Todas las transiciones inválidas deben ser rechazadas con error apropiado
3. El error debe incluir código y mensaje legible
4. Las transiciones exitosas deben ser registradas en auditoría
5. Intentos de transición inválida deben ser logueados
6. Estados ARCHIVADO son terminales (no hay transiciones desde ellos)
7. La implementación debe ser en TournamentService.transition_to()

---

*Artifact: spec*  
*Domain: tournament-state-management*  
*Capability: tournament-state-transitions*  
*Change: tournament-state-flows*  
*Generated: 2026-04-10*