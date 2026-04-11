# Spec: Tournament State Validation

## Overview

Domain: Tournament State Management  
Capability: `tournament-state-validation`  
Change: tournament-state-flows

## Purpose

Definir las validaciones de pre-condición requeridas antes de ejecutar transiciones críticas de estado del torneo. El sistema debe verificar que se cumplen todas las condiciones de negocio antes de permitir cambios de estado, retornando errores específicos cuando las validaciones fallen.

## Requirements

### Core Requirements

1. **MUST** validar que existe al menos 1 categoría criada antes de INSCRIPCION → VERIFICACION
2. **MUST** validar que todas las categorías tienen el mínimo de atletas requeridos antes de VERIFICACION → EN_CURSO
3. **MUST** verificar que todos los matches están completados antes de EN_CURSO → FINALIZADO
4. **MUST** validar que hay al menos 3 árbitros disponibles antes de VERIFICACION → EN_CURSO
5. **MUST** rechazar transición si pre-condiciones no se cumplen
6. **MUST** retornar lista detallada de validaciones fallidas con código y mensaje
7. **MUST** permitir validar pre-condiciones sin ejecutar la transición (dry-run)

### Secondary Requirements

8. **SHOULD** validar que las categorías tienen árbitros asignados antes de EN_CURSO
9. **SHOULD** validar que el horario del torneo está configurado antes de EN_CURSO
10. **MAY** validar que el tatami está disponible antes de EN_CURSO

## Validation Rules

### Validation 1: Categories Exist

| Condition | Required | Error Code | Error Message |
|-----------|----------|-------------|---------------|
| Al menos 1 categoría criada | Yes | NO_CATEGORIES | Debe crear al menos 1 categoría antes de verificar |

**Applicable Transition**: INSCRIPCION → VERIFICACION

### Validation 2: Minimum Athletes per Category

| Condition | Required | Error Code | Error Message |
|-----------|----------|-------------|---------------|
| Kata: mínimo 4 atletas por categoría | Yes | INSUFFICIENT_ATHLETES | Categoría {name} tiene {count} atletas, mínimo requerido: 4 |
| Kumite: mínimo 4 atletas por categoría | Yes | INSUFFICIENT_ATHLETES | Categoría {name} tiene {count} atletas, mínimo requerido: 4 |

**Applicable Transition**: VERIFICACION → EN_CURSO

**Note**: WKF 2026 permite mínimo 4 atletas para formación de bracket válida.

### Validation 3: All Matches Completed

| Condition | Required | Error Code | Error Message |
|-----------|----------|-------------|---------------|
| Todos los matches de todas las categorías tienen resultado | Yes | MATCHES_INCOMPLETE | Existen {count} matches sin completar |

**Applicable Transition**: EN_CURSO → FINALIZADO

### Validation 4: Arbiters Available

| Condition | Required | Error Code | Error Message |
|-----------|----------|-------------|---------------|
| Al menos 3 árbitros disponibles para el evento | Yes | NO_ARBITERS | Se requieren mínimo 3 árbitros, disponibles: {count} |

**Applicable Transition**: VERIFICACION → EN_CURSO

### Validation 5: Categories Have Arbiters Assigned

| Condition | Required | Error Code | Error Message |
|-----------|----------|-------------|---------------|
| Cada categoría tiene al menos 1 árbitro asignado | No | NO_CATEGORY_ARBITER | Categoría {name} no tiene árbitro asignado |

**Applicable Transition**: VERIFICACION → EN_CURSO (warning)

### Validation 6: Tournament Schedule Configured

| Condition | Required | Error Code | Error Message |
|-----------|----------|-------------|---------------|
| Fecha y hora de inicio configuradas | No | NO_SCHEDULE | El horario del torneo no está configurado |

**Applicable Transition**: VERIFICACION → EN_CURSO (warning)

## Scenarios

### Happy Paths

#### Scenario: Validation Passes - Ready to Verify

**Given** un torneo en estado INSCRIPCION  
**And** existen 2 categorías criadas  
**When** el sistema valida pre-condiciones para transición a VERIFICACION  
**Then** debe retornar que la validación fue exitosa  
**And** debe indicar que las pre-condiciones se cumplen

#### Scenario: Validation Passes - Ready to Start

**Given** un torneo en estado VERIFICACION  
**And** todas las categorías tienen más de 4 atletas  
**And** hay 5 árbitros disponibles  
**And** todas las categorías tienen árbitros asignados  
**When** el sistema valida pre-condiciones para transición a EN_CURSO  
**Then** debe retornar que la validación fue exitosa  
**And** debe indicar que las pre-condiciones se cumplen

#### Scenario: Validation Passes - Ready to Finish

**Given** un torneo en estado EN_CURSO  
**And** todos los matches tienen resultado  
**When** el sistema valida pre-condiciones para transición a FINALIZADO  
**Then** debe retornar que la validación fue exitosa  
**And** debe indicar que las pre-condiciones se cumplen

### Edge Cases

#### Scenario: No Categories Created

**Given** un torneo en estado INSCRIPCION  
**And** no existen categorías criadas  
**When** el sistema valida pre-condiciones para transición a VERIFICACION  
**Then** debe rechazar la transición  
**And** debe retornar error con código NO_CATEGORIES  
**And** debe incluir mensaje indicando que debe crear al menos 1 categoría

#### Scenario: Insufficient Athletes in One Category

**Given** un torneo en estado VERIFICACION  
**And** la categoría "Kata Junior Masculino" tiene 2 atletas  
**And** la categoría "Kumite Senior Femenino" tiene 8 atletas  
**When** el sistema valida pre-condiciones para transición a EN_CURSO  
**Then** debe rechazar la transición  
**And** debe retornar error con código INSUFFICIENT_ATHLETES  
**And** debe incluir el nombre de la categoría con atletas insuficientes

#### Scenario: Multiple Validation Failures

**Given** un torneo en estado INSCRIPCION  
**And** no existen categorías criadas  
**When** el sistema intenta validar y luego ejecutar transición a VERIFICACION  
**Then** debe rechazar la transición  
**And** debe retornar lista de errores  
**And** debe incluir NO_CATEGORIES en la lista

#### Scenario: Not Enough Arbiters

**Given** un torneo en estado VERIFICACION  
**And** todas las categorías tienen atletas suficientes  
**And** hay solo 2 árbitros disponibles  
**When** el sistema valida pre-condiciones para transición a EN_CURSO  
**Then** debe rechazar la transición  
**And** debe retornar error con código NO_ARBITERS  
**And** debe incluir el número de árbitros disponibles

#### Scenario: Incomplete Matches Prevent Finish

**Given** un torneo en estado EN_CURSO  
**And** existen 3 matches sin completar en categoría "Kata Senior"  
**When** el sistema valida pre-condiciones para transición a FINALIZADO  
**Then** debe rechazar la transición  
**And** debe retornar error con código MATCHES_INCOMPLETE  
**And** debe incluir el conteo de matches incompletos

#### Scenario: Dry Run Validation

**Given** un torneo en estado INSCRIPCION  
**And** no existen categorías criadas  
**When** el sistema ejecuta validación en modo dry-run  
**Then** debe retornar resultado de validación sin cambiar el estado  
**And** debe indicar que la validación falló  
**And** debe incluir código NO_CATEGORIES

#### Scenario: Warning-Only Validation Failure

**Given** un torneo en estado VERIFICACION  
**And** todas las validaciones requeridas pasan  
**And** no hay horario configurado (warning)  
**When** el sistema valida pre-condiciones para transición a EN_CURSO  
**Then** debe permitir la transición  
**And** debe incluir warning en el resultado indicando horario no configurado

#### Scenario: All Categories Have Insufficient Athletes

**Given** un torneo en estado VERIFICACION  
**And** todas las 5 categorías tienen menos de 4 atletas  
**When** el sistema valida pre-condiciones para transición a EN_CURSO  
**Then** debe rechazar la transición  
**And** debe retornar múltiples errores de INSUFFICIENT_ATHLETES  
**And** debe listar cada categoría con su conteo actual

## Data Model

### ValidationResult

```python
class ValidationResult:
    valid: bool
    transition: str
    required_validations: List[RequiredValidation]
    warnings: List[Warning]
    errors: List[ValidationError]
    can_proceed: bool


class ValidationError:
    code: str  # NO_CATEGORIES, INSUFFICIENT_ATHLETES, etc.
    message: str
    category_name: str | None  # Para errores específicos de categoría
    current_value: Any
    required_value: Any


class Warning:
    code: str
    message: str
```

### Validation Types

- **REQUIRED**: Si falla, la transición debe ser rechazada
- **WARNING**: Si falla, la transición se permite pero con warning

## Acceptance Criteria

1. La validación debe ejecutarse antes de cualquier transición crítica
2. Todos los errores deben incluir código y mensaje legible
3. Los errores específicos de categoría deben incluir el nombre de la categoría
4. La validación debe permitir modo dry-run para pre-visualización
5. Las advertencias no deben bloquear la transición pero deben ser visibles
6. Las validaciones deben ser ejecutadas por TournamentService.validate_transition()
7. Los resultados deben incluir qué pre-condiciones fallaron y cuáles pasaron

---

*Artifact: spec*  
*Domain: tournament-state-management*  
*Capability: tournament-state-validation*  
*Change: tournament-state-flows*  
*Generated: 2026-04-10*