# Tasks: Kata Scoring System

## Phase 1: Foundation Models

### ✅ TASK-01: Extender modelos base de torneo
**Tipo**: modify
**Archivo(s)**: `kakumi_app/models/tournament_model.py`
**Descripción**: Agregar `KATA_SCORE`, team fields en `Match`, `bunkai_required` y `bunkai_mode` con defaults/nullables seguros.
**Depende de**: ninguna
**Criterio de aceptación**: Modelos importan y exponen campos/enums del design.

### ✅ TASK-02: Crear modelos y errores de Kata
**Tipo**: create
**Archivo(s)**: `kakumi_app/models/kata_model.py`
**Descripción**: Definir enums, excepciones custom, `KataJudgeScore` y `KataRoundStanding` con tipos y relaciones.
**Depende de**: TASK-01
**Criterio de aceptación**: Modelos persistibles cubren contratos del servicio.

### ✅ TASK-03: Preparar fixtures compartidas de Kata
**Tipo**: modify
**Archivo(s)**: `tests/conftest.py`
**Descripción**: Agregar fixtures `sample_judges`, `kata_match`, `kata_category`, `kata_team_category`, `sample_team_2`.
**Depende de**: TASK-01, TASK-02
**Criterio de aceptación**: Fixtures sirven para kata individual y team sin setup duplicado.

## Phase 2: Numerical Scoring TDD

### ✅ TASK-04: RED para score numérico
**Tipo**: test
**Archivo(s)**: `tests/test_kata_scoring_service.py`
**Descripción**: Tests RED para `record_numerical_score`: rango, juez duplicado, mínimo de jueces y ganador numérico.
**Depende de**: TASK-03
**Criterio de aceptación**: `pytest` falla por lógica faltante.

### ✅ TASK-05: Implementar score numérico
**Tipo**: create
**Archivo(s)**: `kakumi_app/services/kata_scoring_service.py`
**Descripción**: Crear servicio e implementar `record_numerical_score` y rama numérica de `calculate_match_winner`.
**Depende de**: TASK-04
**Criterio de aceptación**: TASK-04 pasa y persiste `KataJudgeScore`.

## Phase 3: Flag Voting TDD

### ✅ TASK-06: RED para votos por bandera
**Tipo**: test
**Archivo(s)**: `tests/test_kata_scoring_service.py`
**Descripción**: Tests RED para `record_flag_vote` y winner por bandera: AKA/AO, duplicado, panel completo, mayoría.
**Depende de**: TASK-03, TASK-05
**Criterio de aceptación**: Casos bandera fallan por comportamiento faltante.

### ✅ TASK-07: Implementar votos por bandera
**Tipo**: modify
**Archivo(s)**: `kakumi_app/services/kata_scoring_service.py`
**Descripción**: Implementar `record_flag_vote` y mayoría en `calculate_match_winner`.
**Depende de**: TASK-06
**Criterio de aceptación**: Pasan tests numéricos y de bandera.

## Phase 4: Standings + Tie-breakers TDD

### ✅ TASK-08: RED para victory points
**Tipo**: test
**Archivo(s)**: `tests/test_kata_scoring_service.py`
**Descripción**: Tests RED para `assign_victory_points`: ganador 3 VP, perdedor 0 VP, standings base.
**Depende de**: TASK-07
**Criterio de aceptación**: Tests VP fallan antes de implementar.

### ✅ TASK-09: Implementar victory points
**Tipo**: modify
**Archivo(s)**: `kakumi_app/services/kata_scoring_service.py`, `kakumi_app/models/kata_model.py`
**Descripción**: Implementar `assign_victory_points` y soporte mínimo para persistir VP por ronda.
**Depende de**: TASK-08
**Criterio de aceptación**: VP persisten y TASK-08 pasa.

### ✅ TASK-10: RED para standings y desempates
**Tipo**: test
**Archivo(s)**: `tests/test_kata_scoring_service.py`
**Descripción**: Tests RED para `calculate_standings` y `resolve_tiebreaker`: VP, H2H, votos, extra kata, `bunkai_mode`.
**Depende de**: TASK-09
**Criterio de aceptación**: Suite cubre empate simple, múltiple y team kata.

### ✅ TASK-11: Implementar standings y desempates
**Tipo**: modify
**Archivo(s)**: `kakumi_app/services/kata_scoring_service.py`
**Descripción**: Implementar `calculate_standings` y `resolve_tiebreaker` con cascada WKF 2026 y flag `needs_extra_kata`.
**Depende de**: TASK-10
**Criterio de aceptación**: Orden y flags coinciden con spec.

## Phase 5: Migration + Verification

### ✅ TASK-12: Crear migración Alembic de Kata
**Tipo**: migration
**Archivo(s)**: `alembic/versions/xxxx_add_kata_scoring.py`
**Descripción**: Crear revisión para tablas/campos nuevos, FKs a `referees.id`, defaults/nullables y downgrade.
**Depende de**: TASK-01, TASK-02
**Criterio de aceptación**: Migración cubre schema Kata sin enum migration extra.

### ✅ TASK-13: Verificación final de calidad
**Tipo**: test
**Archivo(s)**: `tests/test_kata_scoring_service.py`, `tests/conftest.py`, `kakumi_app/models/kata_model.py`, `kakumi_app/models/tournament_model.py`, `kakumi_app/services/kata_scoring_service.py`, `alembic/versions/xxxx_add_kata_scoring.py`
**Descripción**: Correr Ruff y pytest finales, corrigiendo desvíos de implementación.
**Depende de**: TASK-11, TASK-12
**Criterio de aceptación**: Ruff y pytest pasan; spec y design cubiertos.
